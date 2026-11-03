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

    def test_run_proof_without_replay_is_an_unproven_risk(self) -> None:
        state = base_envelope()
        proof = proven()
        proof.pop("replay")
        state["results"] = [p2_result(proof=proof)]
        result = finalize(state)
        self.assertEqual(result["review_verdict"], "comment")
        self.assertEqual(result["results"][0]["status"], "insufficient_evidence")

    def test_replay_mismatch_rejects_the_claim_at_any_severity(self) -> None:
        state = base_envelope()
        proof = proven()
        proof["replay"] = {"state": "mismatch"}
        state["results"] = [p2_result(classification="P1", proof=proof)]
        result = finalize(state)
        self.assertEqual(result["results"][0]["status"], "rejected")
        self.assertEqual(result["review_verdict"], "approve")
        self.assertEqual(result["unproven_risks"], [])

    def test_traced_proof_blocks_only_with_execution_blocker_and_replay(self) -> None:
        state = base_envelope()
        traced = {"level": "traced", "execution_blocked": "requires_credentials: production identity provider", "replay": {"state": "confirmed"}}
        state["results"] = [p2_result(classification="P1", proof=traced)]
        self.assertEqual(derive_verdict(state)["review_verdict"], "request_changes")

    def test_traced_proof_with_free_text_blocker_is_unproven(self) -> None:
        state = base_envelope()
        traced = {"level": "traced", "execution_blocked": "ran out of time", "replay": {"state": "confirmed"}}
        state["results"] = [p2_result(classification="P1", proof=traced)]
        result = finalize(state)
        self.assertEqual(result["review_verdict"], "comment")
        self.assertEqual(result["results"][0]["status"], "insufficient_evidence")

    def test_unrun_or_mismatched_correctness_results_are_dropped_at_any_severity(self) -> None:
        state = base_envelope()
        mismatched = proven()
        mismatched["replay"] = {"state": "mismatch"}
        state["results"] = [p2_result(classification="P3", proof={"level": "anchored"}), p2_result(classification="P3", proof=mismatched)]
        result = finalize(state)
        self.assertEqual([item["status"] for item in result["results"]], ["rejected", "rejected"])
        self.assertEqual(result["review_verdict"], "approve")
        self.assertNotIn("COR-", result["render"]["developer_review"])

    def test_executed_proof_without_evidence_blocks_completion(self) -> None:
        state = base_envelope()
        state["behavior_proofs"] = [{"proof_id": "affected-flow-e2e", "approval_critical": True, "disposition": "executed", "outcome": "held"}]
        result = finalize(state)
        self.assertEqual(result["review_verdict"], "no_verdict")
        self.assertTrue(any("without evidence" in b for b in result["review_completion"]["blockers"]))

    def test_mandatory_proof_cannot_be_not_applicable_and_blocked_needs_reason(self) -> None:
        state = base_envelope()
        state["behavior_proofs"] = [
            {"proof_id": "existing-tests-at-head", "approval_critical": True, "disposition": "not_applicable", "reason": "no tests here"},
            {"proof_id": "stress-boundary", "approval_critical": False, "disposition": "blocked"},
        ]
        result = finalize(state)
        self.assertEqual(result["review_verdict"], "no_verdict")
        blockers = " ".join(result["review_completion"]["blockers"])
        self.assertIn("existing-tests-at-head", blockers)
        self.assertIn("stress-boundary", blockers)

    def test_failed_behavior_proof_without_result_has_no_verdict(self) -> None:
        state = base_envelope()
        state["behavior_proofs"] = [{"proof_id": "affected-flow-e2e", "approval_critical": True, "disposition": "executed", "outcome": "failed", "evidence": "go test -> FAIL"}]
        self.assertEqual(finalize(state)["review_verdict"], "no_verdict")
        state["results"] = [p2_result(behavior_proof_id="affected-flow-e2e")]
        self.assertEqual(finalize(state)["review_verdict"], "request_changes")

    def test_maintainability_without_rule_or_evidence_is_dropped(self) -> None:
        state = base_envelope()
        state["results"] = [{
            "axis": "maintainability", "kind": "maintainability_concern", "classification": "advisory",
            "status": "verified", "title": "Could be split", "location": {"path": "src/a.py"},
        }]
        result = finalize(state)
        self.assertEqual(result["results"][0]["status"], "rejected")
        self.assertEqual(result["review_verdict"], "approve")

    def test_maintainability_blocker_needs_a_documented_rule(self) -> None:
        state = base_envelope()
        state["results"] = [{
            "axis": "maintainability", "kind": "maintainability_concern", "classification": "blocker",
            "status": "verified", "title": "Bypasses repository layer", "location": {"path": "src/a.py"},
            "trigger": "handler queries the database directly", "claim": "use the repository",
            "evidence": [{"path": "src/a.py", "line": 9, "fact": "raw SQL in handler duplicates repo.Users()"}],
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
            {"proof_id": "boundary-properties", "approval_critical": False, "disposition": "executed", "outcome": "held", "evidence": "go test ./pkg -run TestBoundary -> ok"},
        ]
        result = finalize(state)
        self.assertEqual(result["review_verdict"], "comment")
        self.assertIn("no local database", result["render"]["developer_review"])
        state["behavior_proofs"][0].update({"disposition": "executed", "outcome": "held", "evidence": "docker compose up db && go test ./api -run TestSearchE2E -> ok"})
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
