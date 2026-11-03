#!/usr/bin/env python3
"""Mechanical gates between Trident stages.

Each stage's completion criteria in SKILL.md is checked here against the run
artifacts, so an agent cannot move on by asserting it is done. Exit 1 lists
every violation; exit 0 prints GATE PASS.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_state import (  # noqa: E402
    DISPOSITIONS,
    MANDATORY_PROOFS,
    REPORTABLE_LEVELS,
    RUN_PROOF_LEVELS,
    failed_proofs_without_result,
    valid_execution_blocker,
)


def load(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def gate_context(triage: dict[str, Any], context: dict[str, Any], map_status: dict[str, Any]) -> list[str]:
    """Every impact candidate is accounted for; every flow is runnable or explains why not."""
    problems: list[str] = []
    brief = context.get("change_context_brief")
    if not isinstance(brief, str) or len(brief.strip()) < 200:
        problems.append("change_context_brief is missing or shorter than 200 characters")
    if not context.get("safety_facts"):
        problems.append("no safety_facts recorded (the one to three facts the change is safe because of)")
    flows = context.get("affected_flows") or []
    if not flows and any(entry.get("class") == "source" for entry in triage.get("coverage_manifest", [])):
        problems.append("no affected_flows for a source change")
    covered: set[str] = set()
    for index, flow in enumerate(flows):
        name = flow.get("flow") or f"#{index}"
        for field in ("entry_point", "sink"):
            if not flow.get(field):
                problems.append(f"flow {name}: missing {field}")
        if not flow.get("exercise") and not flow.get("cannot_run_reason"):
            problems.append(f"flow {name}: neither `exercise` (how to drive it) nor `cannot_run_reason`")
        covered.update(flow.get("paths") or [])
    impact = context.get("impact_set") or {}
    for cls in impact.get("equivalence_classes") or []:
        if not cls.get("shared_property"):
            problems.append(f"equivalence class {cls.get('representative')}: missing shared_property")
        covered.add(cls.get("representative", ""))
        covered.update(cls.get("members") or [])
    dismissed = {item.get("path") for item in impact.get("dismissed_usages") or [] if item.get("reason")}
    for item in impact.get("dismissed_usages") or []:
        if not item.get("reason"):
            problems.append(f"dismissed usage {item.get('path')}: missing reason")
    shared_units = {item.get("symbol") for item in impact.get("shared_units") or [] if item.get("strategy")}
    for symbol in (triage.get("impact_candidates") or {}).get("symbols") or []:
        if symbol.get("too_common"):
            if symbol["symbol"] not in shared_units:
                problems.append(f"too-common symbol {symbol['symbol']}: no impact_set.shared_units entry with a strategy")
            continue
        for path in symbol.get("usage_files") or []:
            if path not in covered and path not in dismissed:
                problems.append(f"candidate usage {path} ({symbol['symbol']}) is neither in a flow, an equivalence class, nor dismissed with a reason")
    refreshed = set(context.get("refreshed_sections") or [])
    for section in map_status.get("refresh") or []:
        if section not in refreshed:
            problems.append(f"System Map section {section} needed refresh but is not in refreshed_sections")
    return problems


def gate_plan(plan: dict[str, Any], scopes: list[dict[str, Any]], context: dict[str, Any]) -> list[str]:
    """Every required proof and affected flow belongs to exactly one Prover scope."""
    problems: list[str] = []
    if not scopes:
        return ["no prover scopes"]
    proof_owner: dict[str, list[str]] = {}
    flow_owner: dict[str, list[str]] = {}
    for scope in scopes:
        pid = scope.get("prover_id") or "unnamed"
        if not scope.get("worktree"):
            problems.append(f"scope {pid}: no detached worktree path")
        for proof in scope.get("proofs") or []:
            proof_owner.setdefault(proof, []).append(pid)
        for flow in scope.get("flows") or []:
            flow_owner.setdefault(flow, []).append(pid)
    for proof in plan.get("required_proofs") or []:
        owners = proof_owner.get(proof["proof_id"], [])
        if len(owners) != 1:
            problems.append(f"required proof {proof['proof_id']} assigned to {len(owners)} scopes (need exactly 1)")
    for flow in context.get("affected_flows") or []:
        owners = flow_owner.get(flow.get("flow"), [])
        if len(owners) != 1:
            problems.append(f"affected flow {flow.get('flow')} assigned to {len(owners)} scopes (need exactly 1)")
    ceiling = plan.get("agent_ceiling")
    if ceiling and len(scopes) + 1 > ceiling:
        problems.append(f"{len(scopes)} provers plus replay exceed the agent ceiling {ceiling}")
    return problems


def gate_prove(plan: dict[str, Any], envelope: dict[str, Any]) -> list[str]:
    """Every planned proof has a real disposition; every result is provisional and runnable."""
    problems: list[str] = []
    proofs = {proof.get("proof_id"): proof for proof in envelope.get("behavior_proofs") or []}
    for planned in plan.get("required_proofs") or []:
        proof = proofs.get(planned["proof_id"])
        if proof is None:
            problems.append(f"required proof {planned['proof_id']} is missing from behavior_proofs")
            continue
    for proof_id, proof in proofs.items():
        disposition = proof.get("disposition")
        if disposition not in DISPOSITIONS or disposition == "not_checked":
            problems.append(f"proof {proof_id}: disposition {disposition!r} is not a finished disposition")
        elif disposition == "executed" and not proof.get("evidence"):
            problems.append(f"proof {proof_id}: executed without evidence (command plus output excerpt)")
        elif disposition in {"blocked", "not_applicable"} and not proof.get("reason"):
            problems.append(f"proof {proof_id}: {disposition} without a reason")
        if disposition == "not_applicable" and proof_id in MANDATORY_PROOFS:
            problems.append(f"proof {proof_id}: mandatory, cannot be not_applicable")
        if disposition in {"executed", "satisfied_by_ci"} and proof.get("outcome") not in {"held", "failed"}:
            problems.append(f"proof {proof_id}: {disposition} needs outcome held or failed")
    for index, item in enumerate(envelope.get("results") or []):
        name = item.get("title") or f"#{index}"
        if item.get("status") != "provisional" or item.get("id"):
            problems.append(f"result {name}: provers emit status provisional with id null")
        if item.get("axis") != "correctness":
            continue
        proof = item.get("proof") or {}
        level = proof.get("level")
        if level not in REPORTABLE_LEVELS:
            problems.append(f"result {name}: proof level {level!r}; only traced, executed, or reproduced can be reported")
        elif level in RUN_PROOF_LEVELS:
            recipe = proof.get("recipe") or {}
            expect = recipe.get("expect") or {}
            if not recipe.get("command") or not expect.get("head") or not expect.get("failure_signature"):
                problems.append(f"result {name}: recipe needs command, expect.head, and expect.failure_signature")
        elif not valid_execution_blocker(proof.get("execution_blocked")):
            problems.append(f"result {name}: traced proof needs an allowed execution_blocked reason")
    for proof_id in failed_proofs_without_result(envelope):
        problems.append(f"behavior proof {proof_id} failed but no result carries behavior_proof_id={proof_id}")
    return problems


def gate_replay(envelope: dict[str, Any]) -> list[str]:
    """Every result has an independent replay state; nothing is still provisional."""
    problems: list[str] = []
    verification = envelope.get("verification") or {}
    if verification.get("independent") is not True:
        problems.append("verification.independent must be true: replay ran as a separate agent")
    for index, item in enumerate(envelope.get("results") or []):
        name = item.get("title") or f"#{index}"
        status = item.get("status")
        if status not in {"verified", "rejected", "insufficient_evidence"}:
            problems.append(f"result {name}: status {status!r} after replay")
        if item.get("axis") != "correctness":
            continue
        replay = (item.get("proof") or {}).get("replay") or {}
        if not replay.get("state"):
            problems.append(f"result {name}: no proof.replay.state")
        elif status == "verified" and replay.get("state") != "confirmed":
            problems.append(f"result {name}: verified but replay state is {replay.get('state')}")
    for proof_id in failed_proofs_without_result(envelope):
        problems.append(f"behavior proof {proof_id} failed but no result carries behavior_proof_id={proof_id}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("context", "plan", "prove", "replay"))
    parser.add_argument("--triage", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--map-status", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--scopes", type=Path)
    parser.add_argument("--envelope", type=Path)
    args = parser.parse_args()
    if args.stage == "context":
        if not (args.triage and args.context):
            parser.error("context needs --triage and --context")
        problems = gate_context(load(args.triage), load(args.context), load(args.map_status))
    elif args.stage == "plan":
        if not (args.plan and args.scopes and args.context):
            parser.error("plan needs --plan, --scopes, and --context")
        scopes = json.loads(args.scopes.read_text(encoding="utf-8"))
        problems = gate_plan(load(args.plan), scopes, load(args.context))
    elif args.stage == "prove":
        if not (args.plan and args.envelope):
            parser.error("prove needs --plan and --envelope")
        problems = gate_prove(load(args.plan), load(args.envelope))
    else:
        if not args.envelope:
            parser.error("replay needs --envelope")
        problems = gate_replay(load(args.envelope))
    if problems:
        for problem in problems:
            print(f"GATE FAIL {args.stage}: {problem}")
        return 1
    print(f"GATE PASS {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
