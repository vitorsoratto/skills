#!/usr/bin/env python3
"""Forward tests for the deterministic triage collector."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_triage.py"
SPEC = importlib.util.spec_from_file_location("collect_triage", SCRIPT)
COLLECTOR = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(COLLECTOR)


class CollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.git_run("git", "init", "-q")
        self.git_run("git", "config", "user.email", "test@example.invalid")
        self.git_run("git", "config", "user.name", "Trident Test")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "main.py").write_text("value = 1\n", encoding="utf-8")
        (self.repo / "src" / "delete-me.txt").write_text("remove\n", encoding="utf-8")
        self.git_run("git", "add", ".")
        self.git_run("git", "commit", "-qm", "initial")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git_run(self, *command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, cwd=self.repo, text=True, capture_output=True, check=True)

    def collect(self, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_all_local_includes_untracked_and_line_counts(self) -> None:
        (self.repo / "src" / "main.py").write_text("value = 2\nnew = True\n", encoding="utf-8")
        (self.repo / "notes.md").write_text("untracked\n", encoding="utf-8")
        before = sorted(path.name for path in self.repo.iterdir())
        result = self.collect("--mode", "all-local")
        after = sorted(path.name for path in self.repo.iterdir())
        self.assertEqual(before, after)
        entries = {entry["path"]: entry for entry in result["coverage_manifest"]}
        self.assertIn("notes.md", entries)
        self.assertEqual(entries["src/main.py"]["additions"], 2)
        self.assertEqual(result["schema_version"], "trident-triage-v2")

    def test_staged_and_range_cover_renames_deletions_and_special_classes(self) -> None:
        (self.repo / "src" / "main.py").rename(self.repo / "src" / "renamed.py")
        (self.repo / "src" / "old.py").write_text("old\n", encoding="utf-8")
        (self.repo / "src" / "data.lock").write_text("lock\n", encoding="utf-8")
        (self.repo / "src" / "generated.gen.ts").write_text("generated\n", encoding="utf-8")
        (self.repo / "src" / "icon.png").write_bytes(b"\x89PNG\r\n")
        (self.repo / "src" / "delete-me.txt").unlink()
        self.git_run("git", "add", ".")
        staged = self.collect("--mode", "staged")
        classes = {entry["path"]: entry["class"] for entry in staged["coverage_manifest"]}
        self.assertEqual(classes["src/data.lock"], "lockfile")
        self.assertEqual(classes["src/generated.gen.ts"], "generated")
        self.assertEqual(classes["src/icon.png"], "binary")
        self.git_run("git", "commit", "-qm", "rename and add")
        base = self.git_run("git", "rev-parse", "HEAD~1").stdout.strip()
        head = self.git_run("git", "rev-parse", "HEAD").stdout.strip()
        ranged = self.collect("--mode", "range", "--base", base, "--head", head)
        self.assertTrue(any(entry["class"] == "renamed" for entry in ranged["coverage_manifest"]))
        self.assertTrue(any(entry["class"] == "deleted" for entry in ranged["coverage_manifest"]))
        self.assertIsNotNone(ranged["snapshot"]["merge_base"])

    def test_directory_does_not_truncate_large_manifest(self) -> None:
        for index in range(95):
            path = self.repo / "many" / f"file-{index:03d}.txt"
            path.parent.mkdir(exist_ok=True)
            path.write_text(str(index), encoding="utf-8")
        result = self.collect("--mode", "dir", "--dir", "many")
        self.assertEqual(len(result["coverage_manifest"]), 95)

    def test_pr_requires_number_and_unavailable_command_is_structured(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), "--mode", "pr", "--base", "HEAD", "--head", "HEAD"],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--pr is required", result.stderr)

    def test_pr_exact_head_ci_is_distinguished_from_missing_gh(self) -> None:
        head = "b" * 40
        args = SimpleNamespace(mode="pr", pr="42")
        success = {
            "command": ["gh"], "status": "ok", "stdout": json.dumps({
                "number": 42, "headRefOid": head, "baseRefOid": "a" * 40,
                "statusCheckRollup": [{"name": "tests", "state": "SUCCESS", "commit": {"oid": head}}],
            }), "stderr": "", "code": 0,
        }
        with patch.object(COLLECTOR.shutil, "which", return_value="/usr/bin/gh"), patch.object(COLLECTOR, "run", return_value=success):
            evidence, blocked = COLLECTOR.github_evidence(self.repo, args, head)
        self.assertFalse(blocked)
        self.assertTrue(evidence["exact_head"])
        self.assertTrue(evidence["current_ci_available"])

        with patch.object(COLLECTOR.shutil, "which", return_value=None):
            evidence, blocked = COLLECTOR.github_evidence(self.repo, args, head)
        self.assertFalse(evidence["available"])
        self.assertEqual(blocked[0]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
