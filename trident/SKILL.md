---
name: trident
description: Review GitHub pull requests and git changes through deterministic risk triage, adaptive specialist lanes, independent verification, and evidence-backed verdicts. Use for PR review, local diff review, range review, or directory audit when correctness and maintainability matter.
---

# Trident

Run a read-only pipeline: **Resolve -> Collect -> Triage -> Scan -> Verify ->
Judge -> Complete -> Render**. The canonical result envelope and classifications
live in [references/output-contract.md](references/output-contract.md); prompts
must consume it rather than define a competing schema.

## 1. Resolve one Review Snapshot

Detect targets in this order: GitHub PR URL/number, explicit range, directory,
staged, all-local, then unstaged. GitHub PR mode is GitHub-first: resolve the
PR number, base/head refs and SHAs with `gh`, create a detached temporary
worktree at the reviewed head, and register cleanup before dispatch. A local
fallback may inspect resolvable refs when `gh` is unavailable, but must state
that GitHub metadata and CI coverage are absent. Never claim a current PR review
without a resolved head SHA.

## 2. Collect deterministic Triage Evidence

Run the bundled collector with the exact mode arguments:

```bash
python3 scripts/collect_triage.py --repo "$REPO_ROOT" --mode pr --pr "$PR_NUMBER" --base "$BASE_SHA" --head "$HEAD_SHA"
python3 scripts/collect_triage.py --repo "$REPO_ROOT" --mode range --base "$BASE_SHA" --head "$HEAD_SHA"
python3 scripts/collect_triage.py --repo "$REPO_ROOT" --mode unstaged
python3 scripts/collect_triage.py --repo "$REPO_ROOT" --mode staged
python3 scripts/collect_triage.py --repo "$REPO_ROOT" --mode all-local
python3 scripts/collect_triage.py --repo "$REPO_ROOT" --mode dir --dir "$DIRECTORY"
python3 scripts/triage_policy.py --input /path/to/triage-evidence.json --requested-depth quick
```

The Python 3 standard-library collector uses only read-only `git`, `gh`, and
`rg` operations. Its `trident-triage-v2` JSON is deterministic and includes
snapshot identity, complete manifest/line counts, package capabilities, native
scripts, standards/spec candidates, exact-head CI evidence, objective risk
signals, PR state, and structured blocked commands. It never includes full diff
bodies or writes into the reviewed repository.

Read [references/triage-rules.md](references/triage-rules.md). Produce exactly
one Review Plan with a multidimensional Risk Map, axis-specific depth, required
capabilities, topology, required checks, and a Check Disposition target for
every check. `scripts/triage_policy.py` materializes the deterministic minimum
plan; the model may add a concise escalation reason but may not remove a
rule-required item. Display it and continue automatically; the plan is not an
approval gate.

## 3. Apply deterministic gates and budgets

Correctness always runs. Maintainability always runs at baseline. Spec
Alignment requires a valid Requirement Source; its absence is a resolved
`spec_absent` gate and does not block other axes. Activate specialists from the
triage rules, never from intuition alone. Compatible capabilities may share the
Scanner, but every required capability must be represented and pass through the
Verifier.

Budgets are baseline 2, escalated 4, and deep 6 reviewer agents. A PR alone is
not a deep signal. Exceed a ceiling only to settle a concrete P0/P1, a
Maintainability blocker, or contradictory required evidence, and record the
reason in the Review Plan.

## 4. Discover standards, specs, and checks

Use `rg --files` and `rg`, never ordinary `grep`, for repository guidance,
ADRs, native scripts, workflows, specs, and issue references. Apply precedence:
correctness/security/integrity invariants, valid requirements, ADRs and
architectural constraints, repository standards, Thermo heuristics, then style.
Configuration is only `configured`; tooling is `enforced` only when exact-head
CI or a local execution proves it.

Current CI may satisfy an applicable check only when it belongs to the exact
head. Otherwise execute the narrowest discovered repository-native fallback:
focused tests, then affected-package lint/typecheck/build. Record
`executed`, `satisfied_by_ci`, `not_applicable`, `not_checked`, or `blocked` for
each planned check. Do not invent commands.

## 5. Scan and run activated lenses

Dispatch [prompts/scanner-prompt.md](prompts/scanner-prompt.md) with the Review
Snapshot, Triage Evidence, Coverage Manifest, and Review Plan. Load only
activated specialist prompts. All lenses emit provisional axis-specific results
with `id: null` and Coverage Gaps through the canonical envelope.

When the Thermo Gate passes, invoke the
`thermo-nuclear-code-quality-review` skill as a Maintainability lens, not the
Verifier. Its handoff contains only the Review Snapshot, structural signals,
relevant files, repository constraints, and the declared token budget. Map its
output to `axis: maintainability` with `blocker|major|advisory`; never map it to
P-severity correctness. Baseline Maintainability still runs when Thermo is
inactive.

Run `removal-dead-code` only for a changed deletion/deprecation or concrete
Removal Candidate. Require its reachability matrix across references, exports,
routes/jobs/DI/config, tests/docs, dynamic/reflection use, external consumers,
telemetry, and history. Map only to `safe|defer|insufficient|not_removable`;
text search alone cannot produce `safe`.

The Attention Budget compresses P3, advisory, and low-confidence overflow. It
never hides a verified blocker or mandatory requirement gap.

## 6. Verify and judge

Dispatch [prompts/verifier-prompt.md](prompts/verifier-prompt.md). The Verifier
independently re-reads source, falsifies every provisional claim, preserves its
axis, and assigns stable `COR-*`, `MNT-*`, `SPEC-*`, or `REM-*` IDs only after
dedupe and verification. Rejected and insufficient claims remain auditable but
are not findings.

Run the Arbiter only for P0/P1, disputes, material insufficient evidence,
high-risk structural blockers, or contradictory required evidence. The Arbiter
is a final judge, never a replacement for verification.

## 7. Refresh and complete

Before final rendering, re-read the PR head. On movement, compute the old-to-new
delta, rebuild affected manifest entries, and rerun invalidated lanes/checks;
rerun the PR Baseline when invalidation is broad. Refresh at most twice; further
movement ends with `review_superseded` and `no_verdict`. Verify detached
worktree/temporary cleanup before declaring completion.

Use the pure helpers in `scripts/review_state.py` to update the snapshot,
compute `Review Completion`, derive the verdict, and render both Markdown views.
`refresh_snapshot` invalidates affected results/checks; `compute_completion`
requires currentness, manifest coverage, resolved gates, check dispositions,
verified results, and cleanup; `derive_verdict` cannot approve partial or stale
state.

Read [references/output-contract.md](references/output-contract.md). Completion
is `complete`, `partial`, `blocked`, or `review_superseded`, independent of the
verdict. Approval requires complete/current state, resolved required gates,
verified results, no P0/P1/P2 correctness result, no Maintainability blocker, no
mandatory missing/wrong requirement, and no critical blocked/not-checked check.

## 8. Render and publish only on request

Return a compact Developer Review with verdict, current head, blockers, and
check summary. Put P3/advisories/Coverage Gaps/supporting detail under
`<details>`. When findings exist, also return one Remediation Markdown report
using the same stable IDs and complete handoff context. Do not expose private
chain-of-thought, emit a parallel JSON report, or write into the reviewed repo.

GitHub publication (`gh pr review`, comments, approvals, or change requests)
requires an explicit user request in the current task. The default execution is
read-only.

## Completion criteria

Finish only when the snapshot is current, every manifest entry is accounted for,
all gates are explicit, every planned check has a disposition, every reported
result is verified, rendering is complete, and temporary state is cleaned up.

## References

- [references/output-contract.md](references/output-contract.md): canonical envelope, IDs, lifecycle, and rendering.
- [references/review-contract.md](references/review-contract.md): gates, evidence, freshness, and cleanup.
- [references/triage-rules.md](references/triage-rules.md): deterministic signals, Risk Map, capabilities, and budgets.
- [references/module-playbook.md](references/module-playbook.md): specialist activation and contracts.
- [references/tool-playbook.md](references/tool-playbook.md): evidence-tool selection and freshness.
- [references/removal-plan.md](references/removal-plan.md): Removal Gate evidence matrix.
