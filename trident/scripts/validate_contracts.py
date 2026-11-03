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
        "triage", "context", "prover", "spec-alignment", "removal-dead-code",
        "thermo", "replay", "completion", "render",
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
        "context-prompt.md", "prover-prompt.md", "replay-prompt.md",
        "removal-dead-code-prompt.md", "spec-alignment-prompt.md",
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
    frontmatter = skill.split("---", 2)[1] if skill.startswith("---") else ""
    for line in frontmatter.strip().splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if value and not value.startswith(('"', "'")) and ": " in value:
            fail(f"SKILL.md frontmatter `{key}` has an unquoted ': ' that strict YAML parsers reject", failures)
    for proof_field in ("proof:", "behavior_proofs:", "system_context:", "unproven_risks:"):
        if proof_field not in output:
            fail(f"proof field missing from canonical contract: {proof_field}", failures)
    for reference in (
        "output-contract.md", "review-contract.md", "triage-rules.md", "proof-protocol.md",
        "system-map.md", "risk-questions.md", "evidence-basis.md",
    ):
        if reference not in skill or not (ROOT / "references" / reference).exists():
            fail(f"unresolved skill reference: {reference}", failures)
    for helper in ("collect_triage.py", "triage_policy.py", "review_state.py", "system_map.py", "replay_proofs.py", "stage_gate.py"):
        if not (ROOT / "scripts" / helper).exists():
            fail(f"deterministic helper missing: {helper}", failures)
    for path in sorted(ROOT.rglob("*.md")):
        for target in re.findall(r"\]\(([^)#]+\.md)\)", path.read_text(encoding="utf-8")):
            if not (path.parent / target).resolve().exists():
                fail(f"broken link in {path.relative_to(ROOT)}: {target}", failures)

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print(f"validated canonical contract and {len(declared)} prompt templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
