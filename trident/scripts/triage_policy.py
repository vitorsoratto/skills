#!/usr/bin/env python3
"""Build a deterministic Trident Risk Map and Review Plan from Triage Evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CAPABILITY_RULES = {
    "auth_trust": ("security-trust", "focused-auth-input", "auth-policy"),
    "persistence_data": ("data-integrity", "focused-persistence", "retry-idempotency"),
    "contracts": ("contract-integration", "producer-consumer-contract", "focused-integration"),
    "ui_runtime": ("ui-runtime", "focused-ui", "ui-state-matrix"),
    "edge_functions": ("edge-functions", "essential-path", "boundary-path"),
}


def present_signals(evidence: dict[str, Any]) -> set[str]:
    return {
        name for name, value in (evidence.get("signals") or {}).items()
        if isinstance(value, dict) and value.get("present")
    }


def risk_level(files: int, lines: int, signals: set[str], *, critical: bool = False) -> str:
    if critical:
        return "critical"
    if files > 10 or lines > 100 or len(signals) >= 2:
        return "high"
    if files > 1 or lines > 10 or signals:
        return "medium"
    return "low"


def build_plan(evidence: dict[str, Any], requested_depth: str | None = None) -> dict[str, Any]:
    signals = present_signals(evidence)
    files = int(evidence.get("files_changed", len(evidence.get("coverage_manifest", []))) or 0)
    lines = int(evidence.get("total_lines_changed", 0) or 0)
    ci = evidence.get("ci") or {}
    github = evidence.get("github") or {}
    critical_signals = bool({"auth_trust", "persistence_data"} & signals)
    risk = {
        "scope": risk_level(files, lines, signals),
        "correctness": risk_level(files, lines, signals, critical=critical_signals),
        "contract": "high" if "contracts" in signals else risk_level(files, lines, signals),
        "structural": "high" if {"structural_growth", "deletion_deprecation"} & signals else risk_level(files, lines, signals),
        "runtime": "high" if "ui_runtime" in signals else risk_level(files, lines, signals),
        "requirement": "medium" if evidence.get("issue_reference_candidates") or (evidence.get("repository_capabilities") or {}).get("spec_candidates") else "low",
        "evidence": "high" if (evidence.get("evidence") or {}).get("blocked_commands") or not ci.get("current_ci_available") else "medium",
        "pr_state": "high" if evidence.get("mode") == "pr" and not github.get("exact_head") else "low",
    }
    active = {"correctness", "maintainability"}
    checks: list[dict[str, Any]] = [
        {"check_id": "coverage-manifest", "required": True, "disposition": "not_checked", "target": "complete manifest"},
        {"check_id": "source-verification", "required": True, "disposition": "not_checked", "target": "current source"},
    ]
    for signal, (capability, *check_ids) in CAPABILITY_RULES.items():
        if signal not in signals:
            continue
        active.add(capability)
        checks.extend({"check_id": check_id, "required": True, "disposition": "not_checked", "target": capability} for check_id in check_ids)

    thermo = bool({"structural_growth", "deletion_deprecation"} & signals) or risk["structural"] == "high"
    if thermo:
        active.add("thermo")
        checks.append({"check_id": "thermo-maintainability", "required": True, "disposition": "not_checked", "target": "Thermo handoff"})
    removal = "deletion_deprecation" in signals
    if removal:
        active.add("removal-dead-code")
        checks.append({"check_id": "removal-reachability", "required": True, "disposition": "not_checked", "target": "Removal Gate matrix"})
    spec_enabled = bool(evidence.get("issue_reference_candidates") or (evidence.get("repository_capabilities") or {}).get("spec_candidates"))
    if spec_enabled:
        active.add("spec-alignment")
        checks.append({"check_id": "spec-coverage", "required": True, "disposition": "not_checked", "target": "Requirement Source"})

    if "source" in {entry.get("class") for entry in evidence.get("coverage_manifest", [])} and "tests" not in signals:
        checks.append({"check_id": "focused-test-verification", "required": True, "disposition": "not_checked", "target": "affected native test"})
    if evidence.get("mode") == "pr" and ci.get("current_ci_available"):
        checks.append({"check_id": "pr-current-ci", "required": True, "disposition": "satisfied_by_ci", "target": "exact head"})
    else:
        checks.append({"check_id": "local-verification-fallback", "required": True, "disposition": "not_checked", "target": "affected native checks"})

    requested = requested_depth if requested_depth in {"quick", "deep"} else None
    if requested == "deep":
        budget = "deep"
    elif thermo or removal or spec_enabled or len(active - {"correctness", "maintainability"}) > 1:
        budget = "escalated"
    else:
        budget = "baseline"
    if requested == "quick" and budget == "baseline":
        budget = "baseline"
    if requested == "quick" and budget != "baseline":
        budget = "escalated"
    depth = {
        "correctness": "deep" if requested == "deep" or critical_signals else "baseline",
        "maintainability": "thermo-depth" if thermo else "baseline",
        "spec_alignment": "deep" if requested == "deep" and spec_enabled else "baseline" if spec_enabled else "skipped",
    }
    if not any(item.get("class") == "source" for item in evidence.get("coverage_manifest", [])):
        checks.append({"check_id": "content-coverage", "required": False, "disposition": "not_applicable", "target": "non-source coverage classes"})
    topology = ["shared-scanner", "shared-verifier"]
    if budget != "baseline":
        topology.append("specialist-lanes")
    if requested == "deep" or critical_signals or risk["structural"] == "high":
        topology.append("conditional-arbiter")
    return {
        "schema_version": "trident-plan-v1",
        "snapshot": evidence.get("snapshot", {}),
        "risk_map": risk,
        "active_capabilities": sorted(active),
        "depth_by_axis": depth,
        "budget": budget,
        "agent_ceiling": {"baseline": 2, "escalated": 4, "deep": 6}[budget],
        "topology": topology,
        "required_checks": checks,
        "thermo_gate": {"active": thermo, "reason": "structural signals" if thermo else "not triggered"},
        "spec_gate": {"active": spec_enabled, "reason": "valid candidate source" if spec_enabled else "spec_absent"},
        "removal_gate": {"active": removal, "reason": "deletion/deprecation signal" if removal else "not triggered"},
        "arbiter_conditions": ["P0/P1", "dispute", "insufficient evidence", "contradictory required evidence"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--requested-depth", choices=("quick", "deep"))
    args = parser.parse_args()
    evidence = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(build_plan(evidence, args.requested_depth), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
