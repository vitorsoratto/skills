#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage_gate import gate_context, gate_plan, gate_prove, gate_replay  # noqa: E402


def triage() -> dict:
    return {
        "coverage_manifest": [{"path": "api/search.go", "class": "source"}],
        "impact_candidates": {"symbols": [
            {"symbol": "SearchUsers", "usage_files": ["api/handlers/users.go", "api/export/users.go"], "too_common": False},
            {"symbol": "GetByID", "usage_files": ["a.go"], "too_common": True},
        ]},
    }


def context() -> dict:
    return {
        "change_context_brief": "Intent: the search function now trims the query. " * 8,
        "safety_facts": [{"fact": "pagination totals come from the same query", "proof_id": "affected-flow-e2e", "level": "executed"}],
        "refreshed_sections": ["flows", "operations"],
        "affected_flows": [
            {"flow": "users-list-search", "entry_point": "GET /users?q=", "sink": "JSON page", "changed_symbols": ["SearchUsers"],
             "paths": ["api/handlers/users.go"], "exercise": "go test ./api/handlers -run TestSearch"},
        ],
        "impact_set": {
            "equivalence_classes": [{"representative": "api/handlers/users.go", "members": ["api/export/users.go"], "shared_property": "same SearchUsers options"}],
            "dismissed_usages": [],
            "shared_units": [{"symbol": "GetByID", "strategy": "contract table test on the changed type only"}],
        },
    }


def plan() -> dict:
    return {"agent_ceiling": 2, "required_proofs": [{"proof_id": "affected-flow-e2e"}, {"proof_id": "existing-tests-at-head"}, {"proof_id": "stress-boundary"}]}


def executed(proof_id: str, outcome: str = "held") -> dict:
    return {"proof_id": proof_id, "disposition": "executed", "outcome": outcome, "evidence": "go test ./... -> ok"}


class ContextGateTests(unittest.TestCase):
    def test_complete_context_passes(self) -> None:
        self.assertEqual(gate_context(triage(), context(), {"refresh": ["flows"]}), [])

    def test_unaccounted_usage_and_stale_section_fail(self) -> None:
        ctx = context()
        ctx["impact_set"]["equivalence_classes"] = []
        ctx["refreshed_sections"] = []
        problems = gate_context(triage(), ctx, {"refresh": ["operations"]})
        self.assertTrue(any("api/export/users.go" in p for p in problems))
        self.assertTrue(any("operations" in p for p in problems))

    def test_flow_without_a_way_to_run_fails(self) -> None:
        ctx = context()
        del ctx["affected_flows"][0]["exercise"]
        self.assertTrue(any("cannot_run_reason" in p for p in gate_context(triage(), ctx, {})))


class PlanGateTests(unittest.TestCase):
    def test_every_proof_and_flow_has_one_owner(self) -> None:
        scopes = [{"prover_id": "p1", "worktree": "/tmp/x", "flows": ["users-list-search"], "proofs": ["affected-flow-e2e", "existing-tests-at-head", "stress-boundary"]}]
        self.assertEqual(gate_plan(plan(), scopes, context()), [])
        scopes[0]["proofs"].pop()
        self.assertTrue(any("stress-boundary" in p for p in gate_plan(plan(), scopes, context())))


class ProveGateTests(unittest.TestCase):
    def envelope(self) -> dict:
        return {"behavior_proofs": [executed("affected-flow-e2e"), executed("existing-tests-at-head"), executed("stress-boundary")], "results": []}

    def test_clean_prover_output_passes(self) -> None:
        self.assertEqual(gate_prove(plan(), self.envelope()), [])

    def test_not_checked_executed_without_evidence_and_bad_blocker_fail(self) -> None:
        env = self.envelope()
        env["behavior_proofs"][0]["evidence"] = None
        env["behavior_proofs"][1] = {"proof_id": "existing-tests-at-head", "disposition": "not_applicable", "reason": "no tests"}
        env["behavior_proofs"][2]["disposition"] = "not_checked"
        env["results"] = [{"title": "lost rows", "status": "provisional", "id": None, "axis": "correctness",
                           "proof": {"level": "traced", "execution_blocked": "ran out of time"}}]
        problems = gate_prove(plan(), env)
        self.assertTrue(any("without evidence" in p for p in problems))
        self.assertTrue(any("mandatory" in p for p in problems))
        self.assertTrue(any("not a finished disposition" in p for p in problems))
        self.assertTrue(any("execution_blocked" in p for p in problems))

    def test_failed_proof_needs_a_result(self) -> None:
        env = self.envelope()
        env["behavior_proofs"][0]["outcome"] = "failed"
        self.assertTrue(any("behavior_proof_id" in p for p in gate_prove(plan(), env)))
        env["results"] = [{"title": "search drops last page", "status": "provisional", "id": None, "axis": "correctness", "behavior_proof_id": "affected-flow-e2e",
                           "proof": {"level": "executed", "recipe": {"command": "go test ./api -run TestLastPage", "expect": {"head": "fail", "failure_signature": "got 9 want 10"}}}}]
        self.assertEqual(gate_prove(plan(), env), [])


class ReplayGateTests(unittest.TestCase):
    def test_replay_requires_independence_and_confirmed_state(self) -> None:
        env = {"verification": {"independent": False}, "behavior_proofs": [],
               "results": [{"title": "x", "status": "verified", "axis": "correctness", "proof": {"level": "executed", "replay": {"state": "mismatch"}}}]}
        problems = gate_replay(env)
        self.assertTrue(any("independent" in p for p in problems))
        self.assertTrue(any("mismatch" in p for p in problems))
        env["verification"]["independent"] = True
        env["results"][0]["proof"]["replay"]["state"] = "confirmed"
        self.assertEqual(gate_replay(env), [])


if __name__ == "__main__":
    unittest.main()
