#!/usr/bin/env python3
"""Static checks for the Trident canonical contract and prompt inventory."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"
OUTPUT = ROOT / "references" / "output-contract.md"


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def main() -> int:
    failures: list[str] = []
    output = OUTPUT.read_text(encoding="utf-8")
    required_stages = (
        "triage", "scanner", "edge-functions", "security-trust", "data-integrity",
        "contract-integration", "ui-runtime", "thermo", "removal-dead-code",
        "spec-alignment", "verifier", "arbiter", "completion", "render",
    )
    if "schema_version: trident-result-v1" not in output:
        fail("canonical result schema is missing", failures)
    for stage in required_stages:
        if stage not in output:
            fail(f"stage missing from canonical contract: {stage}", failures)
    for prefix in ("COR-*", "MNT-*", "SPEC-*", "REM-*"):
        if prefix not in output:
            fail(f"stable ID prefix missing: {prefix}", failures)
    for disposition in ("executed", "satisfied_by_ci", "not_applicable", "not_checked", "blocked"):
        if disposition not in output:
            fail(f"check disposition missing: {disposition}", failures)

    declared: dict[str, set[str]] = {}
    required_prompts = {
        "scanner-prompt.md", "edge-functions-prompt.md", "security-trust-prompt.md",
        "data-integrity-prompt.md", "contract-integration-prompt.md", "ui-runtime-prompt.md",
        "removal-dead-code-prompt.md", "spec-alignment-prompt.md", "verifier-prompt.md",
        "arbiter-prompt.md",
    }
    found_prompts = {path.name for path in PROMPTS.glob("*-prompt.md")}
    for missing in sorted(required_prompts - found_prompts):
        fail(f"required prompt missing: {missing}", failures)
    for path in sorted(PROMPTS.glob("*-prompt.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"Fill placeholders:\s*(.+?)\.", text)
        if not match:
            fail(f"placeholder declaration missing: {path.name}", failures)
            continue
        names = set(re.findall(r"\{([A-Z][A-Z0-9_]*)\}", match.group(1)))
        used = set(re.findall(r"\{([A-Z][A-Z0-9_]*)\}", text))
        if used - names:
            fail(f"undeclared placeholders in {path.name}: {sorted(used - names)}", failures)
        if "trident-result-v1" not in text:
            fail(f"prompt does not name canonical schema: {path.name}", failures)
        declared[path.name] = names

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for reference in ("output-contract.md", "review-contract.md", "triage-rules.md", "module-playbook.md"):
        if reference not in skill or not (ROOT / "references" / reference).exists():
            fail(f"unresolved skill reference: {reference}", failures)
    if not (ROOT / "scripts" / "triage_policy.py").exists() or not (ROOT / "scripts" / "review_state.py").exists():
        fail("deterministic triage/state helpers are missing", failures)

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print(f"validated canonical contract and {len(declared)} prompt templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
