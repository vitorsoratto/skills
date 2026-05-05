# Tool Playbook

Use this when deciding how to gather evidence for a Trident review. Prefer repo-local commands and official project workflows over generic guesses.

## Selection Rules

- Start with `git status -sb`, the relevant diff, and `rg`/`rg --files`.
- Use the smallest command that can prove or disprove a claim.
- For external SDKs, frameworks, APIs, browser behavior, or cloud services, read repo docs first and official docs second.
- Do not run destructive commands, production writes, migrations against shared data, or secret-revealing commands.
- If a tool is missing or dependencies are unavailable, record that gap and continue with source evidence.

## Quick Mode

- Scope: `git diff --stat`, focused `git diff`, PR metadata when reviewing a PR.
- Code search: `rg` exact symbols, route names, event names, env vars, and schema fields.
- Verification: one focused unit test, typecheck, lint target, or build target only when it is cheap and repo-supported.
- UI: source inspection plus existing tests unless the suspected bug requires rendering.
- CI: inspect failing check names only when the user asked about CI or the PR status is central.

## Deep Mode

- Scope: include commit intent, reviewed commit SHA, touched ownership boundaries, config/routes, migrations, generated types, and package scripts.
- Code search: trace callers, callees, registrations, serialization/deserialization, auth middleware, persistence boundaries, and peer contract parsers.
- Verification: run focused tests first, then package-level lint/typecheck/build when likely to catch integration mistakes.
- UI: use browser/screenshot/interaction tools for visible regressions when available.
- CI/PR: inspect failing logs, unresolved review threads, and changed workflow files when relevant.
- Docs: consult official docs for unstable or version-sensitive behavior before claiming an SDK/framework/API bug.

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
- `inferred`: follows from code path but was not executed
- `blocked`: useful tool/test was unavailable
- `not_checked`: intentionally out of scope
