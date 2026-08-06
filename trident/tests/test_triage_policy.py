#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from triage_policy import build_plan  # noqa: E402


def evidence(*, signals: dict | None = None, mode: str = "pr", ci: bool = False) -> dict:
    return {
        "mode": mode,
        "files_changed": 1,
        "total_lines_changed": 3,
        "coverage_manifest": [{"path": "src/a.py", "class": "source"}],
        "signals": signals or {},
        "ci": {"current_ci_available": ci},
        "github": {"exact_head": ci},
        "repository_capabilities": {"spec_candidates": []},
        "issue_reference_candidates": [],
        "snapshot": {"base_sha": "a" * 40, "head_sha": "b" * 40},
        "evidence": {"blocked_commands": []},
    }


class TriagePolicyTests(unittest.TestCase):
    def test_tiny_pr_stays_baseline_and_uses_fallback(self) -> None:
        plan = build_plan(evidence())
        self.assertEqual(plan["budget"], "baseline")
        self.assertEqual(plan["agent_ceiling"], 2)
        self.assertNotIn("spec-alignment", plan["active_capabilities"])
        self.assertFalse(plan["spec_gate"]["active"])
        self.assertIn("local-verification-fallback", {item["check_id"] for item in plan["required_checks"]})

    def test_risk_signals_activate_each_required_gate(self) -> None:
        names = {name: {"present": True, "paths": ["src/change.py"], "sources": []} for name in (
            "auth_trust", "persistence_data", "contracts", "ui_runtime", "edge_functions",
            "structural_growth", "deletion_deprecation",
        )}
        rich = evidence(signals=names)
        rich["issue_reference_candidates"] = ["#42"]
        plan = build_plan(rich)
        self.assertEqual(plan["budget"], "escalated")
        for capability in ("security-trust", "data-integrity", "contract-integration", "ui-runtime", "edge-functions", "thermo", "removal-dead-code", "spec-alignment"):
            self.assertIn(capability, plan["active_capabilities"])
        self.assertTrue(plan["thermo_gate"]["active"])
        self.assertTrue(plan["removal_gate"]["active"])
        self.assertTrue(plan["spec_gate"]["active"])

    def test_deep_request_has_six_agent_ceiling_and_exact_ci_disposition(self) -> None:
        plan = build_plan(evidence(mode="pr", ci=True), requested_depth="deep")
        self.assertEqual(plan["budget"], "deep")
        self.assertEqual(plan["agent_ceiling"], 6)
        ci_check = next(item for item in plan["required_checks"] if item["check_id"] == "pr-current-ci")
        self.assertEqual(ci_check["disposition"], "satisfied_by_ci")


if __name__ == "__main__":
    unittest.main()
