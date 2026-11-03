#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from replay_proofs import replay  # noqa: E402


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True, env=env).stdout.strip()


class Fixture:
    """A repository where `charge.py` double-charges at head but not at base."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "charge.py").write_text("def charge(events):\n    return len(set(events))\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base_sha = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "charge.py").write_text("def charge(events):\n    return len(events)\n")
        git(self.repo, "commit", "-qam", "count every delivery")
        self.head_sha = git(self.repo, "rev-parse", "HEAD")
        self.head = root / "head"
        self.base = root / "base"
        git(self.repo, "worktree", "add", "-q", "--detach", str(self.head), self.head_sha)
        git(self.repo, "worktree", "add", "-q", "--detach", str(self.base), self.base_sha)
        self.proofs = root / "proofs"
        (self.proofs / "cor-1").mkdir(parents=True)
        (self.proofs / "cor-1" / "redelivery_check.py").write_text(
            "from charge import charge\n"
            "n = charge(['evt-1', 'evt-1'])\n"
            "assert n == 1, f'charged {n} times for one redelivered event'\n"
        )

    def recipe(self, **expect: str) -> dict:
        return {
            "id": "COR-1",
            "recipe": {
                "files": [{"source": "cor-1/redelivery_check.py", "dest": "trident_proof/redelivery_check.py"}],
                "command": "PYTHONPATH=. python3 trident_proof/redelivery_check.py",
                "timeout_seconds": 30,
                "expect": expect,
            },
        }

    def close(self) -> None:
        self.tmp.cleanup()


class ReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def tearDown(self) -> None:
        self.fx.close()

    def test_differential_replay_confirms_regression_and_cleans_up(self) -> None:
        proof = self.fx.recipe(head="fail", base="pass", failure_signature=r"charged 2 times")
        report = replay([proof], self.fx.head, self.fx.base, self.fx.proofs)
        result = report["results"][0]
        self.assertEqual(result["state"], "confirmed")
        self.assertEqual(result["differential"], "introduced_by_change")
        self.assertFalse((self.fx.head / "trident_proof").exists())
        self.assertEqual(git(self.fx.head, "status", "--porcelain"), "")

    def test_failure_for_another_reason_is_a_mismatch(self) -> None:
        proof = self.fx.recipe(head="fail", failure_signature=r"connection refused")
        report = replay([proof], self.fx.head, None, self.fx.proofs)
        self.assertEqual(report["results"][0]["state"], "mismatch")

    def test_expected_failure_without_signature_is_blocked(self) -> None:
        report = replay([self.fx.recipe(head="fail")], self.fx.head, None, self.fx.proofs)
        self.assertEqual(report["results"][0]["state"], "blocked")

    def test_branch_checkout_is_refused(self) -> None:
        proof = self.fx.recipe(head="fail", failure_signature="charged")
        report = replay([proof], self.fx.repo, None, self.fx.proofs)
        self.assertEqual(report["results"][0]["state"], "blocked")
        self.assertIn("branch", report["results"][0]["head"]["reason"])

    def test_proof_never_overwrites_existing_source(self) -> None:
        proof = self.fx.recipe(head="fail", failure_signature="charged")
        proof["recipe"]["files"][0]["dest"] = "charge.py"
        report = replay([proof], self.fx.head, None, self.fx.proofs)
        self.assertEqual(report["results"][0]["state"], "blocked")
        self.assertIn("len(events)", (self.fx.head / "charge.py").read_text())


class SystemMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()
        self.cache = tempfile.TemporaryDirectory()
        self.env = {**os.environ, "TRIDENT_CACHE_DIR": self.cache.name}

    def tearDown(self) -> None:
        self.cache.cleanup()
        self.fx.close()

    def run_map(self, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "system_map.py"), *args, "--repo", str(self.fx.repo)],
            text=True, capture_output=True, check=True, env=self.env,
        )
        return json.loads(result.stdout)

    def test_map_lives_outside_repo_and_tracks_staleness(self) -> None:
        created = self.run_map("init")
        self.assertTrue(created["dir"].startswith(self.cache.name))
        self.assertEqual(git(self.fx.repo, "status", "--porcelain"), "")
        status = self.run_map("status", "--head", self.fx.head_sha)
        self.assertEqual(status["sections"]["flows"]["state"], "unmapped")

        self.run_map("stamp", "--section", "flows", "--sha", self.fx.base_sha, "--anchor", "charge.py")
        self.run_map("stamp", "--section", "hazards", "--sha", self.fx.base_sha, "--anchor", "docs/")
        status = self.run_map("status", "--head", self.fx.head_sha)
        self.assertEqual(status["sections"]["flows"]["state"], "stale")
        self.assertEqual(status["sections"]["flows"]["drifted_anchors"], ["charge.py"])
        self.assertEqual(status["sections"]["hazards"]["state"], "fresh")
        self.assertIn("flows", status["refresh"])
        self.assertNotIn("hazards", status["refresh"])

    def test_anchor_must_be_repository_relative(self) -> None:
        self.run_map("init")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "system_map.py"), "stamp", "--repo", str(self.fx.repo),
             "--section", "flows", "--sha", self.fx.head_sha, "--anchor", "../outside"],
            text=True, capture_output=True, env=self.env,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
