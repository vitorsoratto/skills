---
name: trident
description: Tool-aware, modular code review pipeline with quick/deep modes, adversarial edge-case review, independent verification, and evidence-based judgment.
---

# Trident

Three-pronged code review pipeline: **Scan -> Verify -> Judge**.

Combines multi-lens scanning with independent verification to produce high-confidence findings while keeping false positives low.

**Core principle:** Scan broadly, route to the right tools and specialist modules, verify independently, judge on evidence from real source files.

## When to Use

- Code review of git changes, PRs, commit ranges, and staged diffs
- Deep codebase audit for bugs, security issues, and logic errors
- Post-implementation review of complex features
- Security or correctness review before release
- Reviews where false positives are more expensive than missing minor style issues

**Do not use for:** style-only reviews, trivial one-line changes, or generic "improve code quality" requests without a review target.

## Review Axes

Trident has three separate axes:

1. **Review mode**: what to review
2. **Review depth**: how aggressively to review it
3. **Active modules**: which specialist lenses to run

### Review Modes

Trident supports **6 review modes**:

| Mode | Trigger | Primary Source | Notes |
|------|---------|----------------|-------|
| `unstaged` | Default when no target is specified | `git diff` | Working tree changes not yet staged |
| `staged` | User says "staged" or unstaged diff is empty | `git diff --cached` | Changes staged for commit |
| `all-local` | User says "all local" or "everything" | `git diff HEAD` | Staged plus unstaged |
| `pr` | User provides PR URL/number or says "review PR" | `gh pr diff {N}` | Remote pull request review |
| `range` | User provides `A..B`, branch, tag, or "since X" | `git diff {A}..{B}` | Multi-commit review |
| `dir` | User provides a directory path | Source files in that path | Full directory audit |

### Review Depths

| Depth | Trigger | Pipeline | Use When |
|-------|---------|----------|----------|
| `quick` | User says "quick" or auto-selected for small local diffs | Scanner + active quick modules -> Verifier | Fast triage, small diffs, day-to-day reviews |
| `deep` | User says "deep"/"full" or auto-selected for broad/risky scopes | Scanner + active deep modules -> Verifier -> Arbiter | PRs, ranges, directories, risky code, or disputed findings |

**Auto-depth selection:**

```text
1. If user explicitly says "quick" or "fast" -> quick
2. If user explicitly says "deep", "full", or "thorough" -> deep
3. If mode is pr, range, or dir -> deep
4. If changed files > 8 or changed lines > 250 -> deep
5. If auth, billing, persistence, migrations, or concurrency paths are involved -> deep
6. Otherwise -> quick
```

### Core Chain and Specialist Modules

Trident has a fixed core chain plus optional specialist modules. Do **not** treat the core itself as a module:

1. `Scanner` creates provisional findings.
2. `Verifier` contests every Scanner and module finding.
3. `Arbiter` runs in `deep` mode and contests both prior stages.

Specialist modules feed provisional findings, test ideas, or coverage gaps into the core. They never bypass the Verifier.

Every module must declare both `quick` and `deep` behavior:

| Module | Activate When | Quick Use | Deep Use |
|--------|---------------|-----------|----------|
| `edge-functions` | Functions, handlers, validators, bug fixes, new feature logic | Validate the essential path plus the top 3 non-happy inputs/states; max 4 module findings | Avoid happy-path bias; build an adversarial matrix across boundary, ordering, failure, auth, and concurrency states; include one essential smoke path |
| `security-trust` | Auth, tenant/ownership, input, files, URLs, secrets, permissions | Inspect changed trust boundary and immediate callers | Trace attacker-controlled data, authz matrix, config/dependency risk, and cross-boundary failure modes |
| `data-integrity` | Persistence, migrations, queues, billing, counters, state machines | Check transactions, idempotency, and direct write ordering | Trace retries, partial writes, races, rollback paths, backfills, and migration compatibility |
| `contract-integration` | API schemas, SDKs, webhooks, clients, jobs, external services | Check caller/callee contract, error shape, and version assumptions | Read local docs plus official external docs when relevant; verify timeout, retry, pagination, and compatibility behavior |
| `ui-runtime` | UI state, forms, routing, browser behavior, frontend data flow | Check critical render/interaction path and obvious empty/error states | Exercise invalid, empty, loading, permission, responsive, accessibility, and browser-runtime states with browser tools when available |
| `removal-dead-code` | Deletions, deprecated paths, unused branches, simplification requests | Only report obvious removal candidates from touched scope | Search call sites, tests, route/config registration, history, and produce a safe deletion plan |

Load `references/module-playbook.md` when module selection is unclear or the review needs a deeper checklist.

### Tool Selection Rules

Use the lightest tool that can prove or disprove the claim. Build a short `TOOL_PLAN` before dispatching agents.

| Evidence Need | Quick Tooling | Deep Tooling |
|---------------|---------------|--------------|
| Scope and intent | `git status`, `git diff --stat`, focused `git diff`, PR metadata | commit history, branch comparison, PR discussion/checks when available |
| Locate source and callers | `rg --files`, `rg`, direct file reads | broader call graph search, route/config registration, generated types, package boundaries |
| Behavior verification | smallest relevant unit/test/typecheck command from repo scripts | focused tests plus lint/typecheck/build for touched package; add reproduction or table tests when cheap |
| External API/SDK/framework behavior | local docs and source contracts | official docs first, then current repo usage; do not guess unstable API behavior |
| UI/runtime behavior | source inspection and existing tests | browser/screenshot/interaction tools for visible regressions when available |
| CI/PR state | `gh pr view`, `gh pr diff` | `gh pr checks`, failing logs, unresolved review threads when relevant |
| Data/migrations | schema/migration files and local dry-run tools | migration rollback/compatibility checks, fixture or local DB verification when safe |

If a useful tool is unavailable, record the gap in `{CONTEXT}` and compensate with source evidence. Never fabricate tool output.

## How to Execute

### Phase 1: Scope and Preflight

Before dispatching agents, determine both `REVIEW_MODE` and `REVIEW_DEPTH`.

#### Step 1: Detect Review Mode

Use this order:

```text
1. GitHub PR URL -> pr
2. PR number (#123) -> pr
3. "PR" or "pull request" -> pr
4. Commit range (abc123..def456) -> range
5. Branch/tag comparison language -> range
6. Directory path -> dir
7. "staged" -> staged
8. "all" or "everything" -> all-local
9. Default -> unstaged
```

#### Step 2: Preflight Tooling

Validate prerequisites before gathering diff context:

```bash
git rev-parse --show-toplevel
git status -sb
command -v rg
```

Additional checks by mode:

- `pr`: require `gh` and verify it can access the target PR
- `range`: verify both refs resolve with `git rev-parse --verify`
- `dir`: verify the directory exists inside the repository

If a prerequisite fails:

- Do not proceed with the full pipeline
- Explain the missing dependency or invalid input
- Offer the closest working fallback, such as reviewing a local diff instead

#### Step 3: Create a Reliable Source Root

Track:

- `REVIEW_MODE`
- `REVIEW_DEPTH`
- `REPO_ROOT`
- `WORKTREE_DIR`
- `TRIDENT_CREATED_WORKTREE`

Initialize:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
WORKTREE_DIR="$REPO_ROOT"
TRIDENT_CREATED_WORKTREE=0
```

For `pr` and `range`, create an isolated worktree in both `quick` and `deep` mode so all agents read real source files without disturbing the user's checkout.

**Mode: `pr`**

```bash
WORKTREE_DIR="/tmp/trident-review-pr-${PR_NUMBER}-$(date +%s)"
git worktree add "$WORKTREE_DIR" --detach
TRIDENT_CREATED_WORKTREE=1
cd "$WORKTREE_DIR"
gh pr checkout "${PR_NUMBER}"
```

**Mode: `range`**

```bash
WORKTREE_DIR="/tmp/trident-review-range-$(echo "${A}..${B}" | tr '/' '-')-$(date +%s)"
git worktree add "$WORKTREE_DIR" "${B}"
TRIDENT_CREATED_WORKTREE=1
```

For `unstaged`, `staged`, `all-local`, and `dir`, keep `WORKTREE_DIR="$REPO_ROOT"`.

#### Step 4: Always Clean Up

Register cleanup immediately after worktree creation so cleanup happens on success, failure, interrupt, or aborted pipeline:

```bash
cleanup_trident_worktree() {
  if [[ "${TRIDENT_CREATED_WORKTREE}" == "1" && "$WORKTREE_DIR" == /tmp/trident-review-* ]]; then
    git worktree remove "$WORKTREE_DIR" --force >/dev/null 2>&1 || true
  fi
}

trap cleanup_trident_worktree EXIT INT TERM
```

Do not postpone cleanup until after reporting. Treat it like a `finally` block.

### Phase 2: Gather Target and Context

Gather executable context commands based on `REVIEW_MODE`.

**Mode: `unstaged`**

```bash
git status -sb
git diff --stat
git diff
```

**Mode: `staged`**

```bash
git status -sb
git diff --cached --stat
git diff --cached
```

**Mode: `all-local`**

```bash
git status -sb
git diff HEAD --stat
git diff HEAD
```

**Mode: `pr`**

```bash
gh pr view "${PR_NUMBER}" --json title,body,author,baseRefName,headRefName,files,additions,deletions
cd "$WORKTREE_DIR" && gh pr diff "${PR_NUMBER}"
```

**Mode: `range`**

```bash
git log --oneline "${A}..${B}"
git diff --stat "${A}..${B}"
git diff "${A}..${B}"
```

**Mode: `dir`**

```bash
rg --files "{DIR}" -g '*.ts' -g '*.tsx' -g '*.js' -g '*.jsx' -g '*.py' -g '*.go' -g '*.rb' -g '*.java' -g '*.kt' -g '*.rs' -g '*.php' | head -50
```

For all modes, enrich context with:

1. Related call sites and contracts using `rg`
2. Entry points, write paths, auth boundaries, and transaction boundaries
3. PR metadata for `pr`
4. Commit messages and intent for `range`
5. High-risk paths such as auth, payments, persistence, migrations, or concurrency
6. `ACTIVE_MODULES`, selected from the module table above
7. `TOOL_PLAN`, including commands already run and useful tools that were unavailable
8. **Edge-case hypotheses** (borrowed from `systematic-debugging` / `tracer`):
   for each modified unit, pre-seed `{CONTEXT}` with candidate failure inputs
   across nullability, emptiness, numeric/collection/string boundaries, time,
   concurrency, failure paths, auth, and input-trust classes. These seeds feed
   the Scanner's mandatory Edge Case Enumeration pass and the `edge-functions`
   module; they apply in both `quick` and `deep` mode.

### Phase 3: Handle Scope Size Explicitly

Use these edge-case rules:

- **Empty diff**: If `unstaged` is empty, auto-try `staged`. If both are empty, ask whether to switch to `pr`, `range`, or `dir`.
- **PR lookup failure**: report the exact `gh` failure and ask for a PR URL/number or local diff fallback.
- **Invalid range**: stop and ask for a valid `A..B`.
- **Large scope**: if changed files > 25, changed lines > 800, or `dir` mode returns > 80 candidate files, batch the review.

#### Large-Scope Batching Procedure

When batching is required:

1. Group files by top-level module or feature area.
2. Create batches capped at **12 files or 400 changed lines**, whichever comes first.
3. Run **Scanner per batch** with `BATCH_ID` in `{CONTEXT}`.
4. Run active specialist modules per batch only when the module has enough local context to be useful.
5. Merge Scanner and module outputs into one provisional finding set.
6. Dedupe provisional findings using this key:
   - normalized category
   - normalized file path
   - normalized trigger or claim
7. Run one Verifier pass on the deduped set.
8. In `deep` mode, run Arbiter only on:
   - all P0 and P1 findings
   - all disputed findings
   - any finding with verifier confidence `low`

Do not send duplicated findings from separate batches to the final report.

### Phase 4: Build Prompt Placeholders

Construct these placeholders for every stage:

- `{TARGET}`: diff text, file list, or directory scope
- `{CONTEXT}`: review metadata, intent, and risk notes
- `{REVIEW_MODE}`: one of the 6 supported modes
- `{REVIEW_DEPTH}`: `quick` or `deep`
- `{WORKTREE_DIR}`: absolute path to the source root agents must inspect
- `{ACTIVE_MODULES}`: selected specialist modules and their quick/deep contracts
- `{TOOL_PLAN}`: tools/commands to use, tools already run, and unavailable-tool gaps
- `{MODULE_OUTPUTS}`: provisional YAML outputs from specialist modules, when present

### Phase 5: Dispatch Pipeline

#### Quick Mode

Run:

1. Scanner
2. Active specialist modules that are cheap enough for `quick`
3. Merge and dedupe provisional findings
4. Verifier

Use quick mode rules:

- Focus on changed files and immediate cross-file effects
- Cap findings at **6**
- Skip dead-code hunting unless it is obvious from the touched scope
- Scanner must still run the **Edge Case Enumeration** pass (see scanner prompt)
  against every modified unit, using the Boundary Conditions section of
  `references/code-quality-checklist.md` plus the hypothesis seeds from Phase 2
- If `edge-functions` is active, run `prompts/edge-functions-prompt.md` or fold its quick checklist into Scanner when separate dispatch is not practical
- Validate that the essential happy path still works, then spend the remaining effort on non-happy paths
- If Verifier returns any `insufficient_evidence`, any P0/P1, or more than 2 rejected scanner findings, recommend rerunning in `deep` mode

#### Deep Mode

Run:

1. Scanner
2. Active specialist modules, with `edge-functions` active by default for feature and bug-fix logic
3. Merge and dedupe provisional findings
4. Verifier
5. Arbiter

Use deep mode rules:

- Full multi-lens scan
- Up to **15 findings**
- Dead-code and removal candidates enabled
- Avoid happy-path bias: validate the essential path once, then prioritize unusual inputs, failed dependencies, boundary sizes, ordering, retries, and permission changes
- Arbiter re-inspects every disputed high-severity item and any finding escalated by the Verifier

### Phase 6: Present to User

After the final stage:

- In `quick` mode, present the Verifier-backed review and clearly flag whether a deep review is recommended.
- In `deep` mode, present the Arbiter-backed verdicts.
- Do **not** implement fixes until the user explicitly asks for changes.

## Shared Output Contract

All agents must emit a single fenced `yaml` block and preserve stable fields across stages.

Required top-level keys:

```yaml
schema_version: trident-v2
stage: scanner
review_mode: unstaged
review_depth: quick
active_modules: []
findings: []
removal_candidates: []
summary: {}
```

`stage` is one of `scanner`, `edge-functions`, `verifier`, or `arbiter`. Future specialist modules may add stage names, but their findings must remain scanner-compatible.

Each item in `findings` must preserve these stable fields:

```yaml
- bug_id: BUG-01
  origin_module: scanner
  title: Short bug title
  location: path/to/file.ext:123
  category: security
  severity: P1
  scanner: {}
  verifier: {}
  arbiter: {}
```

Stage-specific fields:

- `origin_module`: `scanner` or the specialist module that produced the provisional claim
- `scanner.status`: `confirmed` or `suspicious`
- `verifier.status`: `confirmed`, `rejected`, or `insufficient_evidence`
- `arbiter.verdict`: `real_bug`, `not_a_bug`, or `needs_human_check`

Only append stage-specific data. Do not rename keys between stages. Specialist modules must emit scanner-compatible findings with `origin_module` populated; Verifier treats them as provisional first-lane claims.

## Final User Output

Convert the final YAML-backed result into a short human-facing report:

- Files reviewed and overall assessment
- Confirmed bugs
- Dismissed findings
- Needs human review
- Removal candidates if applicable
- Whether a deeper rerun is recommended
- Clear next-step options for the user

If the review is clean, state:

- what was checked
- what was not checked
- residual risks or follow-up tests worth running

## Design Principles

1. **Independent re-inspection.** Each agent reads real source files from `WORKTREE_DIR`.
2. **Executable orchestration.** Examples and shell commands should be directly runnable.
3. **Bounded recall.** Quick mode stays small; deep mode stays selective.
4. **Evidence-based claims.** Every finding needs a location, trigger, and failure story.
5. **Forced counterarguments.** Scanner must explain the strongest reason it could be wrong.
6. **Permission to abstain.** Verifier and Arbiter can preserve ambiguity rather than invent certainty.
7. **Robust cleanup.** Temporary worktrees are always cleaned up.
8. **Review-first.** Never implement without explicit user confirmation.

## Red Flags

**Never:**

- Skip verification and surface Scanner output directly to the user
- Let agents cite diff offsets as source lines
- Use vague pseudo-shell examples that are not executable
- Leave large-diff batching unspecified
- Keep temporary worktrees around after interruption or failure
- Force the full three-stage pipeline for every tiny review
- Run specialist modules without sending their findings through Verifier
- Spend deep mode mostly on happy-path validation
- Implement fixes before the user asks

## Prompt Templates

- `./prompts/scanner-prompt.md`
- `./prompts/edge-functions-prompt.md`
- `./prompts/verifier-prompt.md`
- `./prompts/arbiter-prompt.md`

## References

| File | Purpose |
|------|---------|
| `references/solid-checklist.md` | SOLID smell prompts and refactor heuristics |
| `references/security-checklist.md` | Web/app security and runtime risk checklist |
| `references/code-quality-checklist.md` | Error handling, performance, and boundary conditions |
| `references/removal-plan.md` | Template for deletion candidates and follow-up plan |
| `references/tool-playbook.md` | Tool selection guidance for quick and deep reviews |
| `references/module-playbook.md` | Specialist module activation and quick/deep checklists |
| `references/edge-functions-checklist.md` | Adversarial function-breaking matrix for robust features and bug fixes |
