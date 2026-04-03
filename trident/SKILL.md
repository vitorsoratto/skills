---
name: trident
description: Three-pronged code review pipeline that combines broad scanning, independent verification, and evidence-based judgment.
---

# Trident

Three-pronged code review pipeline: **Scan -> Verify -> Judge**.

Combines multi-lens scanning with independent verification to produce high-confidence findings while keeping false positives low.

**Core principle:** Scan broadly, verify independently, judge on evidence from real source files.

## When to Use

- Code review of git changes, PRs, commit ranges, and staged diffs
- Deep codebase audit for bugs, security issues, and logic errors
- Post-implementation review of complex features
- Security or correctness review before release
- Reviews where false positives are more expensive than missing minor style issues

**Do not use for:** style-only reviews, trivial one-line changes, or generic "improve code quality" requests without a review target.

## Review Axes

Trident has two separate axes:

1. **Review mode**: what to review
2. **Review depth**: how aggressively to review it

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
| `quick` | User says "quick" or auto-selected for small local diffs | Scanner -> Verifier | Fast triage, small diffs, day-to-day reviews |
| `deep` | User says "deep"/"full" or auto-selected for broad/risky scopes | Scanner -> Verifier -> Arbiter | PRs, ranges, directories, risky code, or disputed findings |

**Auto-depth selection:**

```text
1. If user explicitly says "quick" or "fast" -> quick
2. If user explicitly says "deep", "full", or "thorough" -> deep
3. If mode is pr, range, or dir -> deep
4. If changed files > 8 or changed lines > 250 -> deep
5. If auth, billing, persistence, migrations, or concurrency paths are involved -> deep
6. Otherwise -> quick
```

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
4. Merge Scanner outputs into one provisional finding set.
5. Dedupe provisional findings using this key:
   - normalized category
   - normalized file path
   - normalized trigger or claim
6. Run one Verifier pass on the deduped set.
7. In `deep` mode, run Arbiter only on:
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

### Phase 5: Dispatch Pipeline

#### Quick Mode

Run:

1. Scanner
2. Verifier

Use quick mode rules:

- Focus on changed files and immediate cross-file effects
- Cap findings at **6**
- Skip dead-code hunting unless it is obvious from the touched scope
- If Verifier returns any `insufficient_evidence`, any P0/P1, or more than 2 rejected scanner findings, recommend rerunning in `deep` mode

#### Deep Mode

Run:

1. Scanner
2. Verifier
3. Arbiter

Use deep mode rules:

- Full multi-lens scan
- Up to **15 findings**
- Dead-code and removal candidates enabled
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
findings: []
removal_candidates: []
summary: {}
```

Each item in `findings` must preserve these stable fields:

```yaml
- bug_id: BUG-01
  title: Short bug title
  location: path/to/file.ext:123
  category: security
  severity: P1
  scanner: {}
  verifier: {}
  arbiter: {}
```

Stage-specific fields:

- `scanner.status`: `confirmed` or `suspicious`
- `verifier.status`: `confirmed`, `rejected`, or `insufficient_evidence`
- `arbiter.verdict`: `real_bug`, `not_a_bug`, or `needs_human_check`

Only append stage-specific data. Do not rename keys between stages.

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
- Implement fixes before the user asks

## Prompt Templates

- `./prompts/scanner-prompt.md`
- `./prompts/verifier-prompt.md`
- `./prompts/arbiter-prompt.md`

## References

| File | Purpose |
|------|---------|
| `references/solid-checklist.md` | SOLID smell prompts and refactor heuristics |
| `references/security-checklist.md` | Web/app security and runtime risk checklist |
| `references/code-quality-checklist.md` | Error handling, performance, and boundary conditions |
| `references/removal-plan.md` | Template for deletion candidates and follow-up plan |
