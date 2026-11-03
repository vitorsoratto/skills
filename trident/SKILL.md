---
name: trident
description: "Review GitHub pull requests and git changes by proving behavior. Builds a persistent map of how the system works, runs the affected flows end to end with stress cases, and reports only bugs a replayed run confirms. Use for PR review, local diff review, range review, directory audit, or a bounded review-and-fix-until-clean campaign."
---

# Trident

Trident reviews a change by running it. It learns how the system around the
change works, proves the affected flows still do what they should, turns each
suspicion into a runnable prediction, and keeps only the bugs an independent
replay confirms. Tokens go to execution, not to reviewers arguing.

Pipeline: **Resolve -> Collect -> Context -> Plan -> Prove -> Replay ->
Finalize -> Render**. Shapes live in
[references/output-contract.md](references/output-contract.md); proof rules in
[references/proof-protocol.md](references/proof-protocol.md). The research
behind this design is in [references/evidence-basis.md](references/evidence-basis.md).

## Campaign routing: review and fix until clean

When the request alternates Trident and Trident Fix, invokes a review/fix loop,
or asks to keep fixing until clean, run one bounded `trident-converge` campaign.
The campaign owns continuation; individual Trident reviews never authorize the
next fix.

Use this sequence:

1. Run one complete Trident baseline at a resolved PR head and initialize the
   convergence ledger from its finalized `trident-result-v1` envelope (the
   output of `scripts/review_state.py finalize`, so unproven claims are
   already out of `results`).
2. When the deterministic decision is `needs_fix`, send only open blocking
   ledger entries to Trident Fix. Require behavioral proof and a delivery record
   keyed by the persistent `TC-*` campaign key.
3. Run a closure review that replays every prior Proof Recipe (each must now
   pass at the fixed head), then proves the exact fix delta, affected
   callers/contracts/tests, and invalidated checks. Establish differential
   provenance for every newly fingerprinted blocking result.
4. Read the deterministic campaign decision. Only `needs_fix` permits a second
   correction. The campaign ceiling is two corrections and is not configurable
   above two.

Classify closure results before deciding:

- `repeat_prior` or `root_cause_not_fixed`: the semantic finding is already in
  the ledger;
- `fix_regression`: differential evidence proves the behavior was absent before
  the fix and the finding is anchored in the fix delta;
- `preexisting_uncovered`: differential evidence proves the blocker predates
  the fix;
- `insufficient_provenance`: the origin cannot be established.

Terminal decisions are mandatory: `converged` finishes cleanly;
`discovery_incomplete`, `non_convergent`, and `blocked` finish with
`no_verdict`. A terminal decision starts neither another Trident review nor
another fix. P3, advisories, non-mandatory Spec results, Removal results, and
Coverage Gaps remain reported without authorizing a correction cycle.

Load the installed `trident-converge` skill for its campaign artifact contract,
semantic fingerprinting, CLI commands, and deterministic decision helper.

**Completion:** the campaign has one terminal decision, every blocking ledger
entry is accounted for, and no authorized correction or review cycle remains.

## 1. Resolve one Review Snapshot

Detect targets in this order: GitHub PR URL/number, explicit range, directory,
staged, all-local, then unstaged. In PR mode resolve the PR number, base/head
refs, and SHAs with `gh`. Create a run directory outside the repository
(`RUN_DIR=$(mktemp -d -t trident)`) and a detached worktree at the reviewed
head inside it; register cleanup before anything else runs. Without `gh`,
review resolvable local refs and state that GitHub metadata and CI are absent.

**Completion:** a resolved head SHA (and base SHA for PR/range), a detached
worktree under `$RUN_DIR`, and cleanup registered.

## 2. Collect Triage Evidence

```bash
python3 scripts/collect_triage.py --repo "$REPO_ROOT" --mode pr --pr "$PR_NUMBER" --base "$BASE_SHA" --head "$HEAD_SHA" > "$RUN_DIR/triage.json"
# other modes: --mode range --base --head | staged | unstaged | all-local | dir --dir "$DIRECTORY"
python3 scripts/triage_policy.py --input "$RUN_DIR/triage.json" [--requested-depth quick|deep] > "$RUN_DIR/plan.json"
```

The collector is read-only. Besides the manifest, signals, CI, and specs, it
reports `verification_assets` (verify skills, harnesses, related tests per
changed file, native targets), `change_history` (recent commits and fix/revert
history per touched file), and `github.execution_trust`.

The policy emits the minimum Review Plan: Risk Map, capabilities, required
checks, `required_proofs`, `stress_profile`, and agent budget. You may add an
item with a one-line reason; never remove a policy item. Read
[references/triage-rules.md](references/triage-rules.md). Show the plan and
continue; it is not an approval gate.

**Completion:** `triage.json` and `plan.json` exist, and every required check
and proof has a pending disposition.

## 3. Build context before judging anything

Read [references/system-map.md](references/system-map.md).

1. Run `scripts/system_map.py status` (or `init` on the first review of this
   repository). Refresh every section it lists: re-read anchors, correct the
   text, `stamp` at the reviewed head.
2. Build the **Impact Set** from `impact_candidates`: confirm every usage of
   each changed symbol, follow changed data (fields, columns, payloads, masks)
   to every reader and writer, and walk each usage up to its entry point. Only
   the Impact Set is tested; never the whole codebase.
3. Write the Change Context Brief: intent, affected flows (entry point ->
   changed symbols -> sink), contracts on both sides, the one to three safety
   facts the change depends on, existing tests and what they exercise, how to
   run each flow, and hazards from history.
4. Discover standards with `rg --files`/`rg`: AGENTS.md, CLAUDE.md,
   CONTRIBUTING, ADRs, specs. Precedence: correctness/security/integrity
   invariants, valid requirements, ADRs, repository standards, then heuristics.

Use [prompts/context-prompt.md](prompts/context-prompt.md) as a subagent at
deep depth or when the map is missing; otherwise do it yourself.

**Completion:** every candidate usage is confirmed into a flow, covered by an
equivalence class, or dismissed with a reason; every affected flow has an
entry point, a sink, and either a way to exercise it or a recorded reason it
cannot run; every section in `refresh` is stamped.

## 4. Plan the proofs

Decide the **Execution Trust Gate**: run PR code only for a same-repository PR
(`execution_trust.same_repository`), a local mode, or a fork the user
explicitly allowed. Otherwise all proofs are `blocked: untrusted_fork_code`
and Provers work at the `traced` level.

Split the work into Prover scopes by affected flow, near 400 changed lines or
20 files each, within the plan's budget. Give each scope its flows, the
[risk questions](references/risk-questions.md) for its active capabilities,
its required proofs, and the stress profile. When a valid Requirement Source
exists, map each mandatory acceptance criterion to a Behavior Proof.
A required proof that cannot apply here (for example, a migration proof when
the diff only mentions a schema in a comment) gets `not_applicable` with the
evidence; that is a disposition, not a removal.

**Completion:** every required proof and every affected flow is assigned to
exactly one Prover scope.

## 5. Prove

Dispatch [prompts/prover-prompt.md](prompts/prover-prompt.md), one Prover per
scope, in parallel, each in its own detached worktree under `$RUN_DIR`. A
Prover first proves the change works (essential path of each flow, required
proofs, stress), then proves or drops each suspicion with a Proof Recipe.
Run [prompts/spec-alignment-prompt.md](prompts/spec-alignment-prompt.md) when
the Spec Gate is open and
[prompts/removal-dead-code-prompt.md](prompts/removal-dead-code-prompt.md)
for deletions. Run the `thermo-nuclear-code-quality-review` skill as the
Maintainability lens only when the Thermo Gate passes and the skill is installed.

Merge Prover output: one result per root cause, all locations kept. Apply the
signal policy in [references/proof-protocol.md](references/proof-protocol.md);
drop anything that is not a proven or traced wrong outcome. Satisfy remaining
required checks with exact-head CI or the narrowest repository-native command.

**Completion:** every required proof and check has a disposition, and every
provisional result carries a Proof Recipe or a traced path with its
`execution_blocked` reason.

## 6. Replay

Create fresh detached worktrees at head and base. Write every recipe to
`$RUN_DIR/proofs.json`. Dispatch [prompts/replay-prompt.md](prompts/replay-prompt.md):
it audits each recipe without the Prover's reasoning, runs
`scripts/replay_proofs.py`, re-traces traced claims, and sets each result to
`verified`, `rejected`, or `insufficient_evidence`. Disagreements are settled
by one more discriminating run, never by debate.

**Completion:** every provisional result has a replay state, and every
`verified` blocker shows `confirmed`.

## 7. Refresh and finalize

Re-read the PR head before rendering. On movement, compute the delta, rerun
invalidated proofs and checks, and refresh at most twice; further movement ends
with `review_superseded`. Remove worktrees, stop processes this run started
(by PID), and remove containers and scratch state; keep `$RUN_DIR/artifacts`
until rendering ends. Then:

```bash
python3 scripts/review_state.py finalize --input "$RUN_DIR/envelope.json" --cleanup-verified > "$RUN_DIR/final.json"
```

`finalize` applies the proof gate (unproven blockers become Unproven risks),
assigns `COR-*`/`MNT-*`/`SPEC-*`/`REM-*` IDs, computes completion, and derives
the verdict: `request_changes` for a confirmed blocker; `comment` for
non-blocking results, Unproven risks, or a failed Behavior Proof; `approve`
only when the review is complete and every approval-critical proof held;
`no_verdict` when incomplete.

**Completion:** `final.json` has a verdict, and cleanup is verified.

## 8. Render and publish only on request

Return `render.developer_review`: verdict, head, blockers with their proof
line, Unproven risks, Behavior Proofs, and checks, with P3/advisories/gaps
under `<details>`. When verified results exist, also return
`render.remediation_markdown`; each item carries its Proof Recipe so Trident
Fix can rerun it before and after the fix. Return output in the response;
write files only when the user names a destination outside the repository.

Publishing to GitHub (`gh pr review`, comments, approvals, change requests)
requires an explicit user request in the current task.

## Completion criteria

Finish only when the snapshot is current, every manifest entry is accounted
for, every planned check and proof has a disposition, every reported blocker
was confirmed by replay, the System Map is stamped, rendering is complete, and
temporary state is cleaned up.

## References

- [references/proof-protocol.md](references/proof-protocol.md): proof levels, recipes, Behavior Proofs, stress, replay, execution safety, signal policy.
- [references/system-map.md](references/system-map.md): persistent System Map and the Change Context Brief.
- [references/output-contract.md](references/output-contract.md): canonical envelope, IDs, lifecycle, and rendering.
- [references/review-contract.md](references/review-contract.md): gates, evidence, freshness, and cleanup.
- [references/triage-rules.md](references/triage-rules.md): signals, Risk Map, required proofs, stress, and budgets.
- [references/risk-questions.md](references/risk-questions.md): question banks per capability.
- [references/tool-playbook.md](references/tool-playbook.md): finding how to run things, quick and deep modes.
- [references/removal-plan.md](references/removal-plan.md): Removal Gate evidence matrix.
- [references/evidence-basis.md](references/evidence-basis.md): research behind the design.
