#!/usr/bin/env python3
"""Pure helpers for the Trident proof gate, freshness, completion, verdict, and rendering."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DISPOSITIONS = {"executed", "satisfied_by_ci", "not_applicable", "not_checked", "blocked"}
BLOCKING_CORRECTNESS = {"P0", "P1", "P2"}
PROOF_LEVELS = ("asserted", "anchored", "traced", "executed", "reproduced")
RUN_PROOF_LEVELS = {"executed", "reproduced"}


def _verified_results(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in envelope.get("results", []) if item.get("status") == "verified"]


def proof_gate(result: dict[str, Any]) -> str | None:
    """Return why a verified result may not keep its blocking classification, or None.

    Blocking correctness needs a proof that ran the real code and an independent
    replay that confirmed it. A traced proof is accepted only when execution was
    impossible and the replay re-traced it. Maintainability blockers need a
    documented repository rule.
    """
    axis = result.get("axis")
    if axis == "correctness" and result.get("classification") in BLOCKING_CORRECTNESS:
        proof = result.get("proof") or {}
        level = proof.get("level")
        replay = (proof.get("replay") or {}).get("state")
        if level in RUN_PROOF_LEVELS:
            return None if replay == "confirmed" else "run proof was not confirmed by an independent replay"
        if level == "traced" and proof.get("execution_blocked") and replay == "confirmed":
            return None
        if level == "traced":
            return "traced proof without a recorded execution blocker and a confirming replay"
        return f"proof level {level or 'missing'} is below executed"
    if axis == "maintainability" and result.get("classification") == "blocker" and not result.get("rule_anchor"):
        return "maintainability blocker cites no documented repository rule"
    return None


def apply_proof_gate(envelope: dict[str, Any]) -> dict[str, Any]:
    """Downgrade unproven blockers so they inform the human without blocking the PR."""
    state = deepcopy(envelope)
    for item in state.get("results", []):
        if item.get("status") != "verified":
            continue
        reason = proof_gate(item)
        if not reason:
            continue
        item["proof_gate"] = reason
        if item.get("axis") == "maintainability":
            item["classification"] = "major"
        else:
            item["status"] = "insufficient_evidence"
            item["id"] = None
    return state


def unproven_risks(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """Severe claims and approval-critical proofs that could not be settled by execution."""
    risks: list[dict[str, Any]] = []
    for item in envelope.get("results", []):
        if item.get("status") == "insufficient_evidence" and item.get("axis") == "correctness" and item.get("classification") in BLOCKING_CORRECTNESS:
            risks.append({
                "kind": "unproven_claim", "title": item.get("title"), "severity": item.get("classification"),
                "reason": item.get("proof_gate") or (item.get("verification") or {}).get("reason") or "not proven by execution",
                "path": (item.get("location") or {}).get("path"),
            })
    for proof in envelope.get("behavior_proofs") or []:
        if proof.get("approval_critical") and proof.get("disposition") in {"blocked", "not_checked"}:
            risks.append({"kind": "unproven_behavior", "title": proof.get("proof_id"), "severity": None, "reason": proof.get("reason") or proof.get("disposition"), "path": None})
    return risks


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
    state = compute_completion(apply_proof_gate(envelope))
    completion = state["review_completion"]
    if completion["status"] != "complete":
        state["review_verdict"] = "no_verdict"
        return state
    results = _verified_results(state)
    failed_behavior = [proof for proof in state.get("behavior_proofs") or [] if proof.get("outcome") == "failed"]
    if any(_is_blocking(item) for item in results):
        state["review_verdict"] = "request_changes"
    elif results or unproven_risks(state) or failed_behavior:
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
    for proof in state.get("behavior_proofs", []):
        if not proof.get("affected_paths") or affected.intersection(proof["affected_paths"]):
            proof["disposition"] = "not_checked"
            proof.pop("outcome", None)
    if count > 2:
        state["review_completion"] = {"status": "review_superseded", "blockers": ["pull-request head moved more than twice"]}
        state["review_verdict"] = "no_verdict"
    return state


def _proof_line(proof: dict[str, Any] | None) -> str:
    if not proof:
        return "no proof recorded"
    recipe = proof.get("recipe") or {}
    replay = proof.get("replay") or {}
    parts = [str(proof.get("level", "unknown")), f"replay {replay.get('state', 'not run')}"]
    if replay.get("differential"):
        parts.append(str(replay["differential"]).replace("_", " "))
    if recipe.get("command"):
        parts.append(f"`{recipe['command']}`")
    return " · ".join(parts)


def render_developer_review(envelope: dict[str, Any]) -> str:
    state = derive_verdict(finalize_ids(apply_proof_gate(envelope)))
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
            lines.append(f"  - Proof: {_proof_line(item.get('proof'))}")
    else:
        lines.append("- None")
    risks = unproven_risks(state)
    if risks:
        lines.extend(["", "### Unproven risks (need a human or a runnable environment)"])
        for risk in risks:
            severity = f" ({risk['severity']})" if risk.get("severity") else ""
            location = f" — {risk['path']}" if risk.get("path") else ""
            lines.append(f"- {risk.get('title')}{severity}{location}: {risk.get('reason')}")
    proofs = state.get("behavior_proofs") or []
    if proofs:
        lines.extend(["", "### Behavior proven"])
        for proof in proofs:
            outcome = proof.get("outcome") or proof.get("disposition")
            evidence = f" — {proof['evidence']}" if proof.get("evidence") else ""
            lines.append(f"- `{proof.get('proof_id')}`: `{outcome}`{evidence}")
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
    state = finalize_ids(apply_proof_gate(envelope))
    results = _verified_results(state)
    if not results:
        return None
    lines = ["# Trident Remediation Report", ""]
    for item in results:
        location = item.get("location") or {}
        proof = item.get("proof") or {}
        recipe = proof.get("recipe") or {}
        lines.extend([
            f"## {item.get('id')} — {item.get('title')}",
            f"- Axis/classification: `{item.get('axis')}` / `{item.get('classification')}`",
            f"- Anchor: `{location.get('path', 'summary')}:{location.get('start_line', '?')}`",
            f"- Current behavior/trigger: {item.get('trigger', 'not recorded')}",
            f"- Expected behavior: {item.get('claim', 'not recorded')}",
            f"- Impact: {item.get('impact', 'not recorded')}",
            f"- Constraints: {item.get('constraints', 'preserve existing repository contracts')}",
            f"- Bounded correction: {item.get('correction_direction', 'not recorded')}",
            f"- Proof: {_proof_line(proof)}",
        ])
        if recipe:
            lines.append("- Proof Recipe (rerun before and after the fix; head must flip from fail to pass):")
            for file in recipe.get("files") or []:
                lines.append(f"  - add `{file.get('dest')}` from proof file `{file.get('source')}`")
            for step in recipe.get("setup") or []:
                lines.append(f"  - setup: `{step}`")
            lines.append(f"  - run: `{recipe.get('command')}` in `{recipe.get('cwd', '.')}`")
            expect = recipe.get("expect") or {}
            lines.append(f"  - expected at review time: head `{expect.get('head', '?')}`, base `{expect.get('base', 'skip')}`, failure signature `{expect.get('failure_signature', '')}`")
        lines.append("- Checks:")
        for check in item.get("verification_guidance", []):
            lines.append(f"  - {check}")
        for dependency in item.get("dependencies", []):
            lines.append(f"- Dependency/order: {dependency}")
        lines.append("- Evidence Packet:")
        for evidence in item.get("evidence", []):
            lines.append(f"  - `{evidence.get('path')}:{evidence.get('line')}` — {evidence.get('fact')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def finalize(envelope: dict[str, Any]) -> dict[str, Any]:
    """Apply the proof gate, assign IDs, derive the verdict, and render both views."""
    state = derive_verdict(finalize_ids(apply_proof_gate(envelope)))
    state["unproven_risks"] = unproven_risks(state)
    state["render"] = {
        "developer_review": render_developer_review(envelope),
        "remediation_markdown": render_remediation_markdown(envelope),
    }
    return state


def main() -> int:
    import argparse
    import json
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Finalize a Trident envelope: proof gate, IDs, completion, verdict, rendering.")
    parser.add_argument("command", choices=("finalize",))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--cleanup-verified", action="store_true", help="record that worktrees and temporary state were removed")
    args = parser.parse_args()
    envelope = json.loads(args.input.read_text(encoding="utf-8"))
    if args.cleanup_verified:
        envelope["cleanup_verified"] = True
    json.dump(finalize(envelope), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
