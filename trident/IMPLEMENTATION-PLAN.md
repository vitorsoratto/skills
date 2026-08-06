# Trident Reliability Implementation Plan

## Objective

Finish the migration of Trident into a GitHub-first, read-only, risk-triaged review process that is economical for ordinary pull requests and independently verifiable for complex ones.

The decisions in `CONTEXT.md` are authoritative. This plan tracks the work required to make every decision executable. Do not declare the migration complete while any required acceptance criterion below is unmet.

## Current state

Already implemented:

- concise gate-driven workflow in `SKILL.md`;
- conceptual contracts in `CONTEXT.md`;
- initial `triage-rules.md`, `review-contract.md`, and `output-contract.md`;
- initial Python standard-library triage collector;
- read-only publication and artifact-persistence gates;
- adaptive reviewer budgets and optional Spec/Thermo/Removal gates;
- corrected Scanner placeholders and standards/tooling precedence;
- initial skill metadata and README updates.

Known incomplete areas:

- reviewer prompts still use the old universal bug/P0-P3 schema;
- four activated capabilities have no executable prompt;
- Thermo and Removal integrations are declarative rather than operational;
- the collector does not yet gather all required evidence or risk signals;
- triage rules do not yet define a complete signal-to-lane/tool/check mapping;
- completion, refresh, approval, and rendering contracts are not represented in stage outputs;
- no representative forward-test has validated the whole workflow.

## Phase 1 — Define one canonical result contract

### Work

1. Replace the old `trident-v2` universal bug schema with one canonical schema in `references/output-contract.md`.
2. Represent these independently:
   - Correctness: `P0`, `P1`, `P2`, `P3`;
   - Maintainability: `blocker`, `major`, `advisory`;
   - Spec Alignment: `missing`, `partial`, `wrong`, `scope_creep` plus requirement importance;
   - Removal: `safe`, `defer`, `insufficient`, `not_removable`;
   - Coverage Gap: no severity.
3. Define the common Evidence Packet, verification state, check dispositions, Review Completion, Review Verdict, Finding Placement, and stable final IDs.
4. Assign final IDs only after dedupe and verification: `COR-*`, `MNT-*`, `SPEC-*`, `REM-*`.
5. Remove schema definitions duplicated inside prompts. Prompts must reference the canonical contract and add only stage-owned fields.

### Files

- `references/output-contract.md`
- `references/review-contract.md`
- every file under `prompts/`

### Acceptance criteria

- no `BUG-*`, `EDGE-*`, `CONTRACT-*`, or `REMOVE-*` final IDs remain;
- P0-P3 appears only on Correctness results;
- every prompt accepts and emits the same envelope;
- `stage` enums include every executable lane;
- rejected and insufficient claims remain auditable without appearing as verified findings.

## Phase 2 — Complete deterministic triage collection

### Work

Extend `scripts/collect_triage.py` to collect, with timeouts and structured errors:

- repository root, mode, merge-base, base SHA, head SHA, branch names, and PR number;
- complete changed-file status, additions/deletions, total lines, and Coverage Class;
- affected top-level packages/workspaces;
- package manifests and repository-native scripts;
- relevant CI workflows and exact-head GitHub check results;
- repository standards, ADR, spec, PRD, and issue-reference candidates using `rg`/`rg --files`;
- objective signals for auth/trust, persistence/data, contracts, UI/runtime, structural growth, deletion/deprecation, tests, generated files, and migrations;
- evidence availability and blocked commands;
- PR state relevant to freshness and reviewability.

Fix invocation so PR mode always passes the PR number. Keep the collector read-only, dependency-free, deterministic, and free of full diff bodies.

### Files

- `scripts/collect_triage.py`
- `SKILL.md`
- `references/triage-rules.md`

### Acceptance criteria

- JSON output is stable and versioned;
- PR output proves whether CI belongs to the exact reviewed head;
- `all-local` includes tracked and untracked files;
- no candidate list is silently truncated;
- unavailable `git`, `gh`, or `rg` operations become structured `blocked` evidence;
- running the collector creates no file in the reviewed repository.

## Phase 3 — Materialize Risk Map and Review Plan rules

### Work

Define an explicit rule table from Triage Evidence to:

- risk level per dimension: scope, correctness, contract, structural, runtime, requirement, evidence, PR state;
- minimum capabilities;
- required checks and allowed CI satisfaction;
- axis-specific depth;
- baseline, escalated, or deep budget;
- conditions requiring an independent specialist or Arbiter.

Capabilities are coverage obligations, not automatic agent count. Compatible capabilities may share the Scanner. The model may escalate with a concise justification but may not remove rule-required work.

### Files

- `references/triage-rules.md`
- `SKILL.md`
- optionally a deterministic triage-policy script if rules become too fragile for prose

### Acceptance criteria

- the same evidence produces the same minimum Review Plan;
- an ordinary PR stays within two reviewer agents;
- PR mode alone does not trigger deep;
- all confirmed security/data/contract/UI/Thermo/Removal/Spec signals activate their required capability;
- every planned check starts with a declared Check Disposition target.

## Phase 4 — Implement missing review capabilities

### Work

Create executable prompts for:

- `security-trust`;
- `data-integrity`;
- `ui-runtime`;
- `removal-dead-code`.

Update existing `edge-functions`, `contract-integration`, and `spec-alignment` prompts to the canonical axis-specific contract. Remove hard finding caps; use the Attention Budget and compact overflow instead.

Each capability must define quick/baseline and deep behavior, required evidence, abstention behavior, Coverage Gaps, and its completion criterion.

### Files

- new files under `prompts/`
- `prompts/edge-functions-prompt.md`
- `prompts/contract-integration-prompt.md`
- `prompts/spec-alignment-prompt.md`
- `references/module-playbook.md`
- `references/edge-functions-checklist.md`

### Acceptance criteria

- every capability named by a Triage Rule has an executable prompt or an explicit fold-into-Scanner contract;
- no module bypasses independent verification;
- no hard cap can hide a verified blocker or mandatory spec gap;
- absent spec resolves the Spec Gate without asking the user or blocking other axes.

## Phase 5 — Integrate Thermo and Removal operationally

### Work

1. Define the exact handoff from Trident to `thermo-nuclear-code-quality-review` when the Thermo Gate passes.
2. Pass only the Review Snapshot, structural signals, relevant files, repository constraints, and token budget.
3. Map Thermo output into Maintainability results without converting structural concerns into P-severity bugs.
4. Activate `removal-dead-code` only for changed deletion/deprecation or a concrete Removal Candidate.
5. Require reachability evidence across direct references, exports, routes/jobs/DI/config, tests/docs, dynamic/reflection use, and history.
6. Map the result to `safe`, `defer`, `insufficient`, or `not_removable`.

### Files

- `SKILL.md`
- `prompts/removal-dead-code-prompt.md`
- `references/review-contract.md`
- `references/removal-plan.md`

### Acceptance criteria

- Thermo is never used as the Verifier;
- baseline Maintainability still runs when Thermo is inactive;
- Removal never performs a broad repository dead-code hunt by default;
- no deletion is called safe from text search alone.

## Phase 6 — Rebuild Scanner, Verifier, and Arbiter contracts

### Work

- Scanner: produce provisional axis-specific results and Coverage Gaps from real source.
- Verifier: independently falsify each claim, preserve axes, and attach complete Evidence Packets to blockers.
- Arbiter: run only for P0/P1, disputes, insufficient evidence, high-risk structural blockers, or contradictory required evidence.
- Dedupe only same-axis/same-kind results; cross-reference related results across axes.
- Apply Current CI Evidence and Local Verification Fallback with explicit dispositions.

### Files

- `prompts/scanner-prompt.md`
- `prompts/verifier-prompt.md`
- `prompts/arbiter-prompt.md`
- `references/review-contract.md`

### Acceptance criteria

- baseline topology is one shared Scanner plus one Verifier;
- specialist verification is conditional;
- configuration alone is never treated as enforcement;
- every blocking result has claim, trigger, impact, evidence, confidence, correction direction, and verification guidance;
- no cross-axis reranking occurs.

## Phase 7 — Implement freshness and completion state machine

### Work

Represent source refresh explicitly:

1. capture reviewed head;
2. re-read head before final rendering;
3. on movement, compute old-to-new delta;
4. rebuild affected manifest entries and rerun invalidated lanes/checks;
5. rerun PR Baseline when invalidation is broad;
6. stop after two refreshes with `review_superseded`.

Compute Review Completion from currentness, manifest coverage, gate resolution, check dispositions, verified results, and worktree cleanup. Derive Review Verdict only after completion.

### Files

- `SKILL.md`
- `references/output-contract.md`
- orchestration helpers if deterministic state handling warrants scripts

### Acceptance criteria

- stale SHA never produces a current approve/request-changes verdict;
- `partial` cannot claim clean or approve;
- `review_superseded` uses `no_verdict`;
- cleanup is verified before `complete`.

## Phase 8 — Implement compact review and remediation rendering

### Work

Produce two Markdown views from the same verified results:

- Developer Review: verdict, blockers, check summary, concise inline-ready findings, collapsed non-blocking detail;
- Remediation Report: complete context required for another agent to resolve each finding without redoing the review.

Generate the Remediation Report only when findings exist. Return it in the response by default. Never write into the reviewed repository without an explicit destination.

### Files

- `references/output-contract.md`
- rendering prompt or deterministic renderer, if necessary

### Acceptance criteria

- both views use the same stable IDs;
- inline placement requires a precise useful changed line;
- cross-file, architecture, deleted-line, spec, coverage, and review-state findings remain in the summary;
- remediation items include anchors, current/expected behavior, impact, constraints, bounded fix direction, exact discovered checks, dependencies, and Evidence Packet;
- no private chain-of-thought or duplicate JSON report is emitted.

## Phase 9 — GitHub publication boundary

### Work

Keep all review execution read-only. Generate publication-ready content without calling `gh pr review` or creating comments. Only publish after an explicit user request; use the already-derived verdict to choose approve, request-changes, or comment.

### Acceptance criteria

- ordinary `/trident` execution performs no GitHub mutation;
- publishing requires explicit authorization in the current request;
- `no_verdict` is never published as approval or request-changes.

## Phase 10 — Validation and forward tests

### Static validation

- run the official `quick_validate.py`;
- run `git diff --check`;
- validate every prompt placeholder is declared;
- validate the canonical schema and allowed enums;
- verify every `SKILL.md` pointer resolves;
- search for stale contracts: universal P0-P3, `BUG-*`, `REMOVE-*`, hard finding caps, PR-implies-deep, mandatory spec, configured-implies-enforced, ordinary `grep`, and truncated file discovery.

### Collector tests

Cover:

- unstaged with untracked files;
- staged;
- all-local;
- range with rename/deletion/generated/lockfile/binary classes;
- directory with more than 80 files;
- GitHub PR with current CI;
- GitHub PR without CI;
- unavailable `gh` with local-ref fallback;
- timeout/error serialization.

### Forward tests

Use fresh agents with raw repositories/PRs, not this diagnosis:

1. tiny PR with no spec and no CI — baseline budget;
2. ordinary PR with green exact-head CI — avoid redundant checks;
3. auth/data-contract PR — required specialist capabilities;
4. structural refactor — Thermo Gate;
5. deletion/deprecation PR — Removal Gate;
6. PR that changes head during review — refresh and superseded behavior;
7. PR with blocking and advisory findings — compact review plus complete remediation handoff.

### Final Definition of Done

The migration is complete only when:

- every decision in `CONTEXT.md` maps to executable instructions, prompt fields, or deterministic code;
- every named capability has an implementation path;
- no old contract contradicts the canonical references;
- all static and collector tests pass;
- representative forward tests demonstrate budget selection, gate activation, independent verification, freshness, rendering, and read-only behavior;
- `CONTEXT.md` contains no resolved item under `Flagged ambiguities`;
- the final diff has been reviewed for duplication, sediment, and token cost.

## Recommended execution order

Complete phases 1–3 first because every prompt and test depends on the canonical schema and triage contract. Then execute phases 4–6, followed by state/rendering phases 7–9. Finish with phase 10 and do not parallelize edits to the shared canonical contract.
