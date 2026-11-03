#!/usr/bin/env python3
"""Replay Trident Proof Recipes in disposable worktrees and record what happened.

A Proof Recipe is the runnable evidence behind a finding or a Behavior Proof:
files to drop into the worktree, one command, and the expected outcome at the
reviewed head (and optionally at the base). Replaying the recipe in a clean
worktree is Trident's independent verification: the claim stands only if the
code behaves the way the recipe predicts, for the reason it predicts.

Safety rules enforced here:
- every worktree must be a detached git worktree (Trident's own disposable
  checkout), never a branch checkout that may hold user work;
- proof files may only be added, never overwrite an existing file, and must stay
  inside the worktree; they are removed after each run;
- every command has a timeout.

Input (``--proofs``): JSON list, or an object with a ``proofs`` list. Each item:

    {"id": "COR-1",
     "recipe": {"files": [{"source": "cor-1/retry.test.ts", "dest": "src/__trident__/retry.test.ts"}],
                "setup": ["npm ci --prefer-offline"],
                "command": "npx vitest run src/__trident__/retry.test.ts",
                "cwd": ".", "timeout_seconds": 300,
                "expect": {"head": "fail", "base": "pass", "failure_signature": "charged 2 times"}}}

``expect.head``/``expect.base`` are ``pass``, ``fail``, or ``skip``. When a side
is expected to fail, ``failure_signature`` (a regular expression) must match its
output, so a test that fails for an unrelated reason (syntax error, missing
dependency) never confirms a claim.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "trident-replay-v1"
EXCERPT_CHARS = 4000
DEFAULT_TIMEOUT = 300


def is_detached_worktree(path: Path) -> tuple[bool, str]:
    if not path.is_dir():
        return False, f"{path} is not a directory"
    inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, text=True, capture_output=True, check=False)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return False, f"{path} is not a git worktree"
    branch = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=path, text=True, capture_output=True, check=False)
    if branch.returncode == 0:
        return False, f"{path} has branch {branch.stdout.strip()} checked out; replay only runs in detached disposable worktrees"
    return True, "detached"


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def place_files(worktree: Path, proof_root: Path, files: list[dict[str, str]]) -> tuple[list[Path], str | None]:
    """Copy proof files into the worktree; return every file and new directory created."""
    created: list[Path] = []
    for item in files:
        source = (proof_root / item["source"]).resolve()
        dest = worktree / item["dest"]
        if not inside(proof_root, source) or not source.is_file():
            return created, f"proof file {item['source']} is missing or outside the proof root"
        if not inside(worktree, dest):
            return created, f"destination {item['dest']} escapes the worktree"
        if dest.exists():
            return created, f"destination {item['dest']} already exists; proofs may add files but never overwrite source"
        missing = [parent for parent in reversed(dest.parents) if inside(worktree, parent) and not parent.exists()]
        for directory in missing:
            directory.mkdir()
            created.append(directory)
        dest.write_bytes(source.read_bytes())
        created.append(dest)
    return created, None


def remove_files(created: list[Path]) -> None:
    for path in reversed(created):
        try:
            path.rmdir() if path.is_dir() else path.unlink()
        except OSError:
            pass


def text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def run_shell(command: str, cwd: Path, timeout: int, side: str) -> dict[str, Any]:
    env = {**os.environ, "TRIDENT_SIDE": side, "CI": os.environ.get("CI", "1"), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        result = subprocess.run(["bash", "-c", command], cwd=cwd, text=True, capture_output=True, timeout=timeout, env=env, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"outcome": "timeout", "exit_code": None, "output": text(exc.stdout) + text(exc.stderr)}
    return {"outcome": "pass" if result.returncode == 0 else "fail", "exit_code": result.returncode, "output": result.stdout + result.stderr}


def run_side(proof: dict[str, Any], side: str, worktree: Path, proof_root: Path) -> dict[str, Any]:
    recipe = proof.get("recipe") or {}
    expect = (recipe.get("expect") or {}).get(side, "skip")
    if expect == "skip":
        return {"expected": "skip", "outcome": "skipped", "matches_expectation": True}
    ok, reason = is_detached_worktree(worktree)
    if not ok:
        return {"expected": expect, "outcome": "blocked", "reason": reason, "matches_expectation": False}
    cwd = worktree / (recipe.get("cwd") or ".")
    if not inside(worktree, cwd) or not cwd.is_dir():
        return {"expected": expect, "outcome": "blocked", "reason": "cwd is missing or escapes the worktree", "matches_expectation": False}
    timeout = int(recipe.get("timeout_seconds") or DEFAULT_TIMEOUT)
    placed, error = place_files(worktree, proof_root, recipe.get("files") or [])
    try:
        if error:
            return {"expected": expect, "outcome": "blocked", "reason": error, "matches_expectation": False}
        for step in recipe.get("setup") or []:
            setup = run_shell(step, cwd, timeout, side)
            if setup["outcome"] != "pass":
                return {
                    "expected": expect, "outcome": "blocked", "reason": f"setup failed: {step}",
                    "exit_code": setup["exit_code"], "excerpt": setup["output"][-EXCERPT_CHARS:], "matches_expectation": False,
                }
        result = run_shell(str(recipe.get("command") or ""), cwd, timeout, side)
    finally:
        remove_files(placed)
    residue = subprocess.run(["git", "-c", "core.quotePath=false", "status", "--porcelain"], cwd=worktree, text=True, capture_output=True, check=False).stdout.splitlines()
    signature = (recipe.get("expect") or {}).get("failure_signature")
    signature_matched = bool(signature and re.search(signature, result["output"], flags=re.MULTILINE))
    matches = result["outcome"] == expect and (expect != "fail" or signature_matched)
    return {
        "expected": expect,
        "outcome": result["outcome"],
        "exit_code": result["exit_code"],
        "signature_matched": signature_matched if expect == "fail" else None,
        "excerpt": result["output"][-EXCERPT_CHARS:],
        "matches_expectation": matches,
        "worktree_residue": residue[:20],
    }


def classify(head: dict[str, Any], base: dict[str, Any] | None) -> str:
    """Differential classification of one replayed proof."""
    if head.get("outcome") in {"blocked", "timeout"} or (base and base.get("outcome") in {"blocked", "timeout"}):
        return "blocked"
    if not head.get("matches_expectation") or (base and not base.get("matches_expectation")):
        return "mismatch"
    if head.get("expected") == "pass":
        return "behavior_holds"
    if not base or base.get("outcome") == "skipped":
        return "confirmed_head_only"
    if base.get("outcome") == "pass":
        return "introduced_by_change"
    return "preexisting"


def replay(proofs: list[dict[str, Any]], head: Path, base: Path | None, proof_root: Path) -> dict[str, Any]:
    results = []
    for proof in proofs:
        recipe = proof.get("recipe") or {}
        if not recipe.get("command"):
            results.append({"id": proof.get("id"), "state": "blocked", "reason": "recipe has no command"})
            continue
        if (recipe.get("expect") or {}).get("head", "skip") == "fail" and not (recipe.get("expect") or {}).get("failure_signature"):
            results.append({"id": proof.get("id"), "state": "blocked", "reason": "expected failure needs expect.failure_signature"})
            continue
        head_result = run_side(proof, "head", head, proof_root)
        base_result = None
        if base is not None and (recipe.get("expect") or {}).get("base", "skip") != "skip":
            base_result = run_side(proof, "base", base, proof_root)
        state = classify(head_result, base_result)
        results.append({
            "id": proof.get("id"),
            "state": "confirmed" if state not in {"blocked", "mismatch"} else state,
            "differential": state,
            "head": head_result,
            "base": base_result,
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "head_worktree": str(head),
        "base_worktree": str(base) if base else None,
        "results": results,
        "summary": {state: sum(1 for item in results if item.get("state") == state) for state in ("confirmed", "mismatch", "blocked")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proofs", type=Path, required=True)
    parser.add_argument("--proof-root", type=Path, required=True, help="directory holding recipe source files (outside the reviewed repo)")
    parser.add_argument("--head-worktree", type=Path, required=True)
    parser.add_argument("--base-worktree", type=Path)
    args = parser.parse_args()
    data = json.loads(args.proofs.read_text(encoding="utf-8"))
    proofs = data.get("proofs", []) if isinstance(data, dict) else data
    report = replay(proofs, args.head_worktree, args.base_worktree, args.proof_root)
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if not report["summary"]["mismatch"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
