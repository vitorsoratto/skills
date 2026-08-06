#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from review_state import (  # noqa: E402
    derive_verdict,
    render_developer_review,
    render_remediation_markdown,
    refresh_snapshot,
)


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

    def test_blocker_requests_changes_and_renders_same_id(self) -> None:
        state = base_envelope()
        state["results"] = [{
            "axis": "correctness", "kind": "correctness_bug", "classification": "P2",
            "status": "verified", "title": "Wrong fallback", "impact": "user sees stale data",
            "trigger": "dependency returns empty", "claim": "fallback must preserve current value",
            "location": {"path": "src/a.py", "start_line": 4},
            "evidence": [{"path": "src/a.py", "line": 4, "fact": "fallback overwrites value"}],
            "verification_guidance": ["run focused test"], "correction_direction": "retain value",
        }]
        result = derive_verdict(state)
        self.assertEqual(result["review_verdict"], "request_changes")
        review = render_developer_review(state)
        remediation = render_remediation_markdown(state)
        self.assertIn("COR-1", review)
        self.assertIn("COR-1", remediation or "")

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
