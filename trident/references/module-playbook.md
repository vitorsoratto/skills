# Module Playbook

Specialist modules are first-lane reviewers. They generate scanner-compatible findings with `origin_module`, then the Verifier contests them.

## Activation

- `edge-functions`: activate for changed functions, handlers, validators, parsers, mappers, feature logic, and bug fixes.
- `security-trust`: activate for auth, tenant isolation, roles, secrets, URL/file/input handling, CORS, headers, crypto, and dependency trust.
- `data-integrity`: activate for database writes, migrations, queues, billing, inventory, counters, state machines, and retries.
- `contract-integration`: activate for APIs, SDKs, schema changes, webhooks, jobs, clients, serialization, pagination, and version assumptions.
- `ui-runtime`: activate for UI state, forms, routing, browser APIs, responsive behavior, accessibility, and frontend data loading.
- `removal-dead-code`: activate for deletions, deprecated paths, feature flag cleanup, branch pruning, and simplification work.

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

## Merge Rules

When combining module output with Scanner output, dedupe by:

1. normalized category
2. normalized file path
3. normalized trigger
4. normalized wrong outcome

If two modules find the same bug, keep the stronger evidence and add the other module under `cross_references` or `evidence`.
