#!/usr/bin/env python3
"""Pure helpers for Trident freshness, completion, verdict, and rendering."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DISPOSITIONS = {"executed", "satisfied_by_ci", "not_applicable", "not_checked", "blocked"}
BLOCKING_CORRECTNESS = {"P0", "P1", "P2"}


def _verified_results(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in envelope.get("results", []) if item.get("status") == "verified"]


def finalize_ids(envelope: dict[str, Any]) -> dict[str, Any]:
    """Assign deterministic IDs to final results that lack one."""
    state = deepcopy(envelope)
    counters = {"correctness": 0, "maintainability": 0, "spec_alignment": 0, "removal": 0}
    prefixes = {"correctness": "COR", "maintainability": "MNT", "spec_alignment": "SPEC", "removal": "REM"}
    results = sorted(
        _verified_results(state),
        key=lambda item: (
            item.get("axis", ""), item.get("kind", ""), item.get("location", {}).get("path", ""),
            item.get("location", {}).get("start_line", 0), item.get("title", ""),
        ),
    )
    for item in results:
        axis = item.get("axis")
        if axis not in counters or item.get("id"):
            continue
        counters[axis] += 1
        item["id"] = f"{prefixes[axis]}-{counters[axis]}"
    return state


def check_state(envelope: dict[str, Any]) -> tuple[bool, list[str]]:
    checks = envelope.get("check_dispositions") or []
    blockers: list[str] = []
    for check in checks:
        disposition = check.get("disposition")
        if disposition not in DISPOSITIONS:
            blockers.append(f"check {check.get('check_id', 'unknown')} has no valid disposition")
        elif (check.get("required") or check.get("critical")) and disposition in {"blocked", "not_checked"}:
            blockers.append(f"required check {check.get('check_id', 'unknown')} is {disposition}")
    return not blockers, blockers


def compute_completion(envelope: dict[str, Any], *, cleanup_verified: bool | None = None) -> dict[str, Any]:
    """Derive Review Completion without deriving a verdict from stale state."""
    state = deepcopy(envelope)
    snapshot = state.get("review_snapshot") or state.get("snapshot") or {}
    refresh_count = int(snapshot.get("refresh_count", 0) or 0)
    if refresh_count > 2 or snapshot.get("current") == "review_superseded":
        status = "review_superseded"
    else:
        current = snapshot.get("current") is True
        manifest = state.get("coverage_manifest") or {}
        manifest_complete = manifest.get("status") == "complete" or bool(manifest.get("entries")) and all(
            entry.get("treatment") for entry in manifest.get("entries", [])
        )
        checks_ok, check_blockers = check_state(state)
        gates = state.get("gates_resolved", (state.get("review_plan") or {}).get("gates_resolved", True))
        result_states = {item.get("status") for item in state.get("results", [])}
        results_verified = not result_states or result_states.issubset({"verified", "rejected", "insufficient_evidence"})
        cleanup = cleanup_verified if cleanup_verified is not None else bool(state.get("cleanup_verified", False))
        if not snapshot.get("head_sha") or not snapshot.get("base_sha"):
            status = "blocked"
        elif not current:
            status = "partial"
        elif not manifest_complete or not gates or not checks_ok or not results_verified or not cleanup:
            status = "blocked" if check_blockers or state.get("verification", {}).get("state") == "blocked" else "partial"
        else:
            status = "complete"
    current = snapshot.get("current") is True and status != "review_superseded"
    checks_ok, check_blockers = check_state(state)
    manifest = state.get("coverage_manifest") or {}
    manifest_complete = manifest.get("status") == "complete" or bool(manifest.get("entries")) and all(
        entry.get("treatment") for entry in manifest.get("entries", [])
    )
    cleanup = cleanup_verified if cleanup_verified is not None else bool(state.get("cleanup_verified", False))
    completion = {
        "status": status,
        "current_snapshot": current,
        "manifest_complete": manifest_complete,
        "gates_resolved": bool(state.get("gates_resolved", (state.get("review_plan") or {}).get("gates_resolved", True))),
        "checks_resolved": checks_ok,
        "results_verified": not any(item.get("status") == "provisional" for item in state.get("results", [])),
        "cleanup_verified": cleanup,
        "blockers": check_blockers,
    }
    state["review_completion"] = completion
    return state


def _is_blocking(item: dict[str, Any]) -> bool:
    if item.get("axis") == "correctness":
        return item.get("classification") in BLOCKING_CORRECTNESS
    if item.get("axis") == "maintainability":
        return item.get("classification") == "blocker"
    return item.get("axis") == "spec_alignment" and item.get("requirement_importance") == "mandatory" and item.get("classification") in {"missing", "wrong"}


def derive_verdict(envelope: dict[str, Any]) -> dict[str, Any]:
    state = compute_completion(envelope)
    completion = state["review_completion"]
    if completion["status"] != "complete":
        state["review_verdict"] = "no_verdict"
        return state
    results = _verified_results(state)
    if any(_is_blocking(item) for item in results):
        state["review_verdict"] = "request_changes"
    elif results:
        state["review_verdict"] = "comment"
    else:
        state["review_verdict"] = "approve"
    return state


def refresh_snapshot(envelope: dict[str, Any], new_head: str, changed_paths: list[str]) -> dict[str, Any]:
    """Refresh one snapshot and mark affected results/checks for rerun."""
    state = deepcopy(envelope)
    snapshot = state.setdefault("review_snapshot", {})
    old_head = snapshot.get("head_sha")
    if old_head == new_head:
        snapshot["current"] = True
        return state
    count = int(snapshot.get("refresh_count", 0) or 0) + 1
    snapshot.update({"head_sha": new_head, "current": count <= 2, "refresh_count": count, "refreshed_from": old_head})
    affected = set(changed_paths)
    for result in state.get("results", []):
        path = (result.get("location") or {}).get("path")
        if path in affected:
            result["status"] = "provisional"
            result["id"] = None
    for check in state.get("check_dispositions", []):
        if check.get("affected_paths") and affected.intersection(check["affected_paths"]):
            check["disposition"] = "not_checked"
    if count > 2:
        state["review_completion"] = {"status": "review_superseded", "blockers": ["pull-request head moved more than twice"]}
        state["review_verdict"] = "no_verdict"
    return state


def render_developer_review(envelope: dict[str, Any]) -> str:
    state = derive_verdict(finalize_ids(envelope))
    completion = state.get("review_completion", {})
    snapshot = state.get("review_snapshot") or {}
    lines = [
        f"## Trident Review — `{state.get('review_verdict', 'no_verdict')}`",
        f"Review Completion: `{completion.get('status', 'blocked')}` · head `{snapshot.get('head_sha') or 'unknown'}`",
        "",
        "### Blocking results",
    ]
    blocking = [item for item in _verified_results(state) if _is_blocking(item)]
    if blocking:
        for item in blocking:
            lines.append(f"- **{item.get('id')}** — {item.get('title')} ({item.get('classification')}) — {(item.get('location') or {}).get('path', 'summary')}")
            lines.append(f"  - Impact: {item.get('impact', 'not recorded')}")
    else:
        lines.append("- None")
    lines.extend(["", "### Checks"])
    for check in state.get("check_dispositions", []):
        lines.append(f"- `{check.get('check_id')}`: `{check.get('disposition')}`")
    extras = [item for item in _verified_results(state) if not _is_blocking(item)]
    gaps = state.get("coverage_gaps") or []
    if extras or gaps:
        lines.extend(["", "<details>", "<summary>Non-blocking results and coverage gaps</summary>", ""])
        for item in extras:
            lines.append(f"- **{item.get('id')}** — {item.get('title')} ({item.get('classification')})")
        for gap in gaps:
            lines.append(f"- Coverage Gap — {gap.get('area')}: {gap.get('reason')}")
        lines.extend(["", "</details>"])
    return "\n".join(lines)


def render_remediation_markdown(envelope: dict[str, Any]) -> str | None:
    state = finalize_ids(envelope)
    results = _verified_results(state)
    if not results:
        return None
    lines = ["# Trident Remediation Report", ""]
    for item in results:
        location = item.get("location") or {}
        lines.extend([
            f"## {item.get('id')} — {item.get('title')}",
            f"- Axis/classification: `{item.get('axis')}` / `{item.get('classification')}`",
            f"- Anchor: `{location.get('path', 'summary')}:{location.get('start_line', '?')}`",
            f"- Current behavior/trigger: {item.get('trigger', 'not recorded')}",
            f"- Expected behavior: {item.get('claim', 'not recorded')}",
            f"- Impact: {item.get('impact', 'not recorded')}",
            f"- Constraints: {item.get('constraints', 'preserve existing repository contracts')}",
            f"- Bounded correction: {item.get('correction_direction', 'not recorded')}",
            "- Checks:",
        ])
        for check in item.get("verification_guidance", []):
            lines.append(f"  - {check}")
        for dependency in item.get("dependencies", []):
            lines.append(f"- Dependency/order: {dependency}")
        lines.append("- Evidence Packet:")
        for evidence in item.get("evidence", []):
            lines.append(f"  - `{evidence.get('path')}:{evidence.get('line')}` — {evidence.get('fact')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
