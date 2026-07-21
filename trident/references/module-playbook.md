# Module Playbook

Specialist modules are first-lane reviewers. They generate scanner-compatible findings with `origin_module`, then the Verifier contests them.

## Activation

- `edge-functions`: activate for changed functions, handlers, validators, parsers, mappers, feature logic, and bug fixes.
- `security-trust`: activate for auth, tenant isolation, roles, secrets, URL/file/input handling, CORS, headers, crypto, and dependency trust.
- `data-integrity`: activate for database writes, migrations, queues, billing, inventory, counters, state machines, and retries.
- `contract-integration`: activate for APIs, SDKs, schema changes, webhooks, jobs, clients, serialization, pagination, and version assumptions.
- `ui-runtime`: activate for UI state, forms, routing, browser APIs, responsive behavior, accessibility, and frontend data loading.
- `removal-dead-code`: activate for deletions, deprecated paths, feature flag cleanup, branch pruning, and simplification work.
- `spec-alignment`: activate when a linked ticket, issue reference, PRD, or spec file is discoverable from commit messages, PR description, branch name, or repo docs.

## Quick Contract

- Stay close to the changed scope and immediate callers.
- Validate the essential path once.
- Spend most attention on the highest-risk non-happy paths.
- Emit only findings with a concrete trigger and wrong outcome.
- Prefer `deep_review_recommended: true` over broad speculation.

## Deep Contract

- Avoid happy-path bias. After one essential smoke check, focus on unusual states, boundaries, failed dependencies, ordering, permission drift, and concurrent calls.
- Trace cross-module contracts instead of only reading modified lines.
- Use official docs for version-sensitive external behavior.
- Include test ideas only when tied to a concrete suspected failure.
- Record coverage gaps as `areas_not_covered`, not as bugs.

## Contract-Integration Deep Checklist

When `contract-integration` is active, build a producer/consumer matrix before
reporting findings:

- caller parameter names, enum values, flags, date/timezone fields, and defaults
- transport shape: route, query string, body, generated type, DTO, or SDK call
- callee parsing and validation, including ignored fields and fallback defaults
- operation order for server-driven lists, including whether aggregate totals
  are global or page-local
- response metadata, totals/KPIs, and export/download behavior consumed by UI
- source freshness: checked commit and peer contract source used

For server-side collections, never stop after checking only search or only
pagination. Search, filters, sort field names, sort direction, page totals,
grand totals, and exported views are one contract surface.

Only promote a contract finding to P0/P1 when both sides are current and the
wrong outcome is reachable by a normal user or job.

## Spec-Alignment Discovery

Before running the spec-alignment module, discover the spec source in priority
order:

1. **Issue/ticket refs in commit messages** — parse `#NNN`, `Closes #NNN`,
   `Fixes #NNN`, `Resolves #NNN` from `git log` of the reviewed range. This is
   the most common source.
2. **PR description body** — for `pr` mode, check `gh pr view` output for linked
   issues or explicit spec references.
3. **Branch-name ticket patterns** — `feature/PROJ-123-*`, `fix/456-*` → extract
   the ticket ID and fetch via `gh issue view`.
4. **Spec files** — `docs/specs/`, `specs/`, `.scratch/`, or `PRD.md` matching
   the branch or feature name.
5. **User-provided path** — if the user passed a spec file or ticket URL as
   argument.
6. **If nothing is found**, note `SPEC_SOURCE: none` and skip the module.

### Ticket Validation

When a ticket is found, validate it before extracting requirements:

- Fetch full body: `gh issue view {N} --json title,body,state,labels`
- Check status: `open`, `closed`, `blocked`, or `superseded`
- Extract acceptance criteria or checklist items from the body
- Scan body for dependency markers: `blocked by #NNN`, `depends on #NNN`,
  `supersedes #NNN`, `related to #NNN`
- If closed or superseded, note the status and downgrade spec-alignment
  confidence — the diff may be re-implementing or reverting prior work

### Spec-Alignment Quick Contract

- Stay close to the top 3-5 core requirements only
- Report missing core items as findings; note partials in `areas_not_covered`
- Skip scope-creep analysis unless the diff adds clearly unrelated behavior
- Prefer `deep_review_recommended: true` over exhaustive spec enumeration

### Spec-Alignment Deep Contract

- Extract every requirement and acceptance criterion
- Check each: `addressed` / `partial` / `missing`
- Flag scope creep: behavior in the diff that the spec did not ask for
- Flag wrong implementation: requirement present but semantics differ
- Quote the spec line for each finding
- If multiple tickets are linked, check each independently

## Merge Rules

When combining module output with Scanner output, dedupe by:

1. normalized category
2. normalized file path
3. normalized trigger
4. normalized wrong outcome

If two modules find the same bug, keep the stronger evidence and add the other module under `cross_references` or `evidence`.
