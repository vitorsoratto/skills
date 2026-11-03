# Tool Playbook

Use this when deciding how to gather evidence for a Trident review. Prefer repo-local commands and official project workflows over generic guesses.

## Selection Rules

- Start with `git status -sb`, the relevant diff, and `rg`/`rg --files`.
- Use the smallest command that can prove or disprove a claim, then run it.
- For external SDKs, frameworks, APIs, browser behavior, or cloud services, read repo docs first and official docs second.
- Follow the execution safety rules in [proof-protocol.md](proof-protocol.md): disposable worktrees and data only, no production or shared targets, no secret-revealing commands, kill only what you started.
- If a tool is missing or dependencies are unavailable, record that gap and continue with source evidence.

## Finding how to run things

Read `verification_assets` from Triage Evidence first: `verify-*` skills,
browser/mobile harnesses, compose files, load or property-test tools, related
tests per changed file, and native script/Makefile/justfile targets. Then the
System Map `operations` section. Prefer, in order:

1. a `verify-<app>` skill's Launch/Doctor/Drive recipe;
2. the repository's own test runner with its fixtures (focused file or test name);
3. the repository's local stack (compose, dev server, seeded database);
4. a small proof script that imports the real module and calls the changed
   function with real collaborators.

Record each command's outcome in the System Map once it has run.

## Quick Mode

- Scope: `git diff --stat`, focused `git diff`, PR metadata when reviewing a PR.
- Context: refresh only System Map sections touched by the diff.
- Proof: related tests at head plus the essential path of each affected flow;
  prove at most the two strongest suspicions.

## Deep Mode

- Scope: commit intent, reviewed commit SHA, ownership boundaries,
  config/routes, migrations, generated types, and package scripts.
- Context: trace callers, callees, registrations, serialization, auth
  middleware, persistence boundaries, and peer contract parsers into the brief.
- Proof: every required Behavior Proof, the full stress profile, and
  base-differential replay for every result.
- UI: drive the flow with the browser harness and capture an accessibility
  snapshot or screenshot.
- Docs: consult official docs for unstable or version-sensitive behavior before
  claiming an SDK/framework/API bug, and prove it with a run when possible.

## PR Freshness

For PR reviews, capture the reviewed head SHA before creating the worktree and
re-check it before reporting. If the head changed, either rerun against the new
head or report that the review is tied to the older commit.

Useful commands:

```bash
gh pr view "$PR_NUMBER" --json headRefOid,baseRefName,headRefName,commits
git rev-parse HEAD
```

## Contract Tracing

For client/server and cross-package contracts, prefer exact symbol searches over
generic browsing:

```bash
rg -n "sortBy|sortOrder|search|pageSize|grandTotal|hideValues" .
rg -n "Parse|Request|Response|DTO|Schema|params" .
```

When a peer service exists locally, read its DTO/parser/source before accepting
a contract claim as confirmed. If the peer source is unavailable, mark the gap
as `blocked` or `insufficient_evidence`.

## Evidence Labels

Classify every verification step in `{CONTEXT}`:

- `observed`: command or source line directly supports it
- `executed`: a command ran the real code and its output supports it
- `inferred`: follows from code path but was not executed
- `blocked`: useful tool/test was unavailable
- `not_checked`: intentionally out of scope

## Spec and Standards Discovery

### Spec Source

```bash
# Extract ticket refs from commit messages in the reviewed range
git log --oneline --grep='#[0-9]' {A}..{B}
git log --oneline --grep='Closes\|Fixes\|Resolves' {A}..{B}

# Fetch ticket body and metadata
gh issue view {N} --json title,body,state,labels,assignees

# Check for linked or blocking issues
gh issue view {N} --json body --jq .body | rg -i 'blocked|supersedes|related|depends'

# PR description for spec references (pr mode)
gh pr view {PR_NUMBER} --json body
```

### Repo Standards

```bash
# Discover repo documentation files
rg --files -g 'CODING_STANDARDS.md' -g 'CONTRIBUTING.md' -g 'AGENTS.md' -g 'CLAUDE.md' -g '.cursorrules' -g 'docs/**/*.md'

# Detect active tooling configs
rg --files -g '.eslintrc*' -g 'biome.json' -g 'ruff.toml' -g '.golangci*' -g 'clippy.toml' -g '.rubocop*' -g 'tsconfig*.json' -g '.pre-commit-config.yaml' -g '.husky/*'
```
