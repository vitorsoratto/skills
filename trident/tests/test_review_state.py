#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from review_state import (  # noqa: E402
    derive_verdict,
    finalize,
    render_developer_review,
    render_remediation_markdown,
    refresh_snapshot,
)


def proven(command: str = "npx vitest run src/__trident__/a.test.ts") -> dict:
    return {
        "level": "executed",
        "recipe": {"command": command, "expect": {"head": "fail", "base": "pass", "failure_signature": "stale"}},
        "replay": {"state": "confirmed", "differential": "introduced_by_change"},
    }


def p2_result(**overrides) -> dict:
    result = {
        "axis": "correctness", "kind": "correctness_bug", "classification": "P2",
        "status": "verified", "title": "Wrong fallback", "impact": "user sees stale data",
        "trigger": "dependency returns empty", "claim": "fallback must preserve current value",
        "location": {"path": "src/a.py", "start_line": 4},
        "evidence": [{"path": "src/a.py", "line": 4, "fact": "fallback overwrites value"}],
        "verification_guidance": ["run focused test"], "correction_direction": "retain value",
        "proof": proven(),
    }
    result.update(overrides)
    return result


def base_envelope() -> dict:
    return {
        "review_snapshot": {"base_sha": "a" * 40, "head_sha": "b" * 40, "current": True, "refresh_count": 0},
        "coverage_manifest": {"status": "complete", "entries": [{"path": "src/a.py", "treatment": "semantic review"}]},
        "gates_resolved": True,
        "cleanup_verified": True,
        "check_dispositions": [{"check_id": "tests", "required": True, "disposition": "executed"}],
        "results": [],
    }


class ReviewStateTests(unittest.TestCase):
    def test_complete_clean_review_approves(self) -> None:
        result = derive_verdict(base_envelope())
        self.assertEqual(result["review_completion"]["status"], "complete")
        self.assertEqual(result["review_verdict"], "approve")

    def test_proven_blocker_requests_changes_and_renders_same_id(self) -> None:
        state = base_envelope()
        state["results"] = [p2_result()]
        result = derive_verdict(state)
        self.assertEqual(result["review_verdict"], "request_changes")
        review = render_developer_review(state)
        remediation = render_remediation_markdown(state)
        self.assertIn("COR-1", review)
        self.assertIn("introduced by change", review)
        self.assertIn("COR-1", remediation or "")
        self.assertIn("npx vitest run", remediation or "")

    def test_unproven_blocker_becomes_unproven_risk_and_blocks_approval(self) -> None:
        state = base_envelope()
        state["results"] = [p2_result(proof={"level": "anchored"})]
        result = finalize(state)
        self.assertEqual(result["review_verdict"], "comment")
        self.assertEqual(result["results"][0]["status"], "insufficient_evidence")
        self.assertEqual(result["unproven_risks"][0]["kind"], "unproven_claim")
        self.assertIn("Unproven risks", result["render"]["developer_review"])
        self.assertIsNone(result["render"]["remediation_markdown"])

    def test_run_proof_without_replay_is_not_blocking(self) -> None:
        state = base_envelope()
        proof = proven()
        proof["replay"] = {"state": "mismatch"}
        state["results"] = [p2_result(proof=proof)]
        self.assertEqual(derive_verdict(state)["review_verdict"], "comment")

    def test_traced_proof_blocks_only_with_execution_blocker_and_replay(self) -> None:
        state = base_envelope()
        traced = {"level": "traced", "execution_blocked": "needs production identity provider", "replay": {"state": "confirmed"}}
        state["results"] = [p2_result(classification="P1", proof=traced)]
        self.assertEqual(derive_verdict(state)["review_verdict"], "request_changes")

    def test_maintainability_blocker_needs_a_documented_rule(self) -> None:
        state = base_envelope()
        state["results"] = [{
            "axis": "maintainability", "kind": "maintainability_concern", "classification": "blocker",
            "status": "verified", "title": "Bypasses repository layer", "location": {"path": "src/a.py"},
            "trigger": "handler queries the database directly", "claim": "use the repository",
        }]
        result = finalize(state)
        self.assertEqual(result["results"][0]["classification"], "major")
        self.assertEqual(result["review_verdict"], "comment")
        state["results"][0]["rule_anchor"] = "docs/adr/0003-repository-layer.md:12"
        self.assertEqual(finalize(state)["review_verdict"], "request_changes")

    def test_unproven_critical_behavior_prevents_approval(self) -> None:
        state = base_envelope()
        state["behavior_proofs"] = [
            {"proof_id": "affected-flow-e2e", "approval_critical": True, "disposition": "blocked", "reason": "no local database"},
            {"proof_id": "boundary-properties", "approval_critical": False, "disposition": "executed", "outcome": "held"},
        ]
        result = finalize(state)
        self.assertEqual(result["review_verdict"], "comment")
        self.assertIn("no local database", result["render"]["developer_review"])
        state["behavior_proofs"][0].update({"disposition": "executed", "outcome": "held"})
        self.assertEqual(finalize(state)["review_verdict"], "approve")

    def test_refresh_supersedes_after_third_head_move(self) -> None:
        state = base_envelope()
        state = refresh_snapshot(state, "c" * 40, ["src/a.py"])
        state = refresh_snapshot(state, "d" * 40, ["src/a.py"])
        state = refresh_snapshot(state, "e" * 40, ["src/a.py"])
        result = derive_verdict(state)
        self.assertEqual(result["review_completion"]["status"], "review_superseded")
        self.assertEqual(result["review_verdict"], "no_verdict")


if __name__ == "__main__":
    unittest.main()
