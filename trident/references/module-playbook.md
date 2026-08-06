# Module Playbook

Specialist capabilities are coverage obligations, not automatic agent count.
Each emits the canonical `trident-result-v1` envelope with provisional results;
the shared Verifier contests every result.

## Activation

- `edge-functions`: changed functions, handlers, validators, parsers, mappers,
  or feature logic.
- `security-trust`: auth, tenant isolation, roles, secrets, URL/file/input
  handling, CORS, headers, crypto, or dependency trust.
- `data-integrity`: database writes, migrations, queues, billing, counters,
  state machines, retries, or cache invalidation.
- `contract-integration`: APIs, SDKs, schema, webhooks, jobs, clients,
  serialization, pagination, or version assumptions.
- `ui-runtime`: UI state, forms, routing, browser APIs, responsive behavior,
  accessibility, or frontend data loading.
- `removal-dead-code`: changed deletion/deprecation or a concrete Removal
  Candidate only.
- `spec-alignment`: a valid issue, PRD, specification, or implementation-bound
  ADR found by the Spec Gate.
- `thermo`: the Thermo Gate is passed; invoke the external maintainability skill
  with its restricted handoff and map its output to Maintainability.

## Shared contract

Read `references/output-contract.md` before dispatch. Stay close to changed
scope and immediate callers, validate the essential path once, then prioritize
non-happy paths indicated by Triage Evidence. Emit only concrete triggers and
wrong outcomes. Use `coverage_gaps` for unsupported or unexecuted areas.

Quick depth uses the highest-risk applicable boundary cases. Deep depth traces
cross-module contracts, failed dependencies, ordering, permission drift,
concurrency, and version-sensitive external behavior. Use official docs for
unstable external behavior when necessary.

## Contract-integration matrix

For server-side collections, inspect caller names/defaults, route/query/body,
DTO/parser validation, errors, search, filters, sort field/direction, page and
grand totals, exports, retry/timeout behavior, and source freshness. Do not
promote a cross-boundary result to P0/P1 without current producer and consumer
evidence and a reachable normal user/job trigger.

## Spec Gate

Discover in this order: commit issue references; PR description; branch ticket;
matching spec/PRD files; user-provided path. Validate issue state and acceptance
criteria. If no valid source exists, record `spec_absent` and skip the lens; do
not ask the user or block other axes. A closed/superseded issue lowers
confidence unless the PR explicitly targets it.

## Merge and dedupe

Deduplicate only same-axis/same-kind results using normalized path, trigger,
and wrong outcome. Preserve cross-axis relationships through
`cross_references`. Stable IDs are assigned only after the Verifier confirms a
result; rejected and insufficient results remain auditable without IDs.
