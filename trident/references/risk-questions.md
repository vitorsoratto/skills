# Risk Questions

Specialist capabilities are question banks for the Prover, not separate
reviewer agents. Load only the sections activated by the Review Plan. Each
question is a hypothesis to prove or drop with the
[Proof Protocol](proof-protocol.md); a question that cannot be turned into a
runnable or traceable prediction is dropped, not reported.

Pick the three to five questions most relevant to the affected flows. Depth
comes from proving a few well, not from asking all of them.

## edge-functions

Changed functions, handlers, validators, parsers, mappers, or feature logic.

- Does the essential path produce the intended output for a minimal valid
  input from a real caller?
- Which of absent/empty values, numeric limits, ordering, unicode/time,
  dependency failure, retries, concurrency, identity, and trust-boundary input
  does the change newly expose? Prove the top three with a table or a property
  test.
- Does any caller pass a value the new code no longer accepts?

See [edge-functions-checklist.md](edge-functions-checklist.md) for boundary
classes.

## security-trust

Auth, tenant isolation, roles, secrets, URL/file/input handling, CORS/CSRF,
headers, crypto, or dependency trust.

- For each changed boundary, does a request with the wrong identity, tenant,
  or role get rejected, and the right one accepted? Build the matrix as a test.
- Is the policy enforced where the data is read or written, not only at a
  route that a second entry point can bypass?
- Can attacker-controlled input reach a query, path, URL, template, shell, or
  deserializer? Feed it hostile values.
- Do failures fail closed, without leaking secrets or internals in errors or
  logs?

See [security-checklist.md](security-checklist.md).

## data-integrity

Writes, migrations, transactions, queues, counters, billing, caches, retries,
state machines.

- Does a write through the changed path read back correctly through a second,
  independent path?
- Does redelivery, retry, or double submit leave exactly one effect?
- Do N concurrent executions keep the invariant?
- What happens when a dependency fails halfway: rollback, partial state, or
  duplicate?
- Does the migration apply to a disposable copy with representative data, and
  roll back or is it explicitly forward-only? Does old code still run against
  the new schema during deploy?
- Is every cache that holds the changed data invalidated?

## contract-integration

APIs, DTOs, events, webhooks, SDKs, jobs, serialization, pagination, version
assumptions.

- Does the real producer's output parse in the real consumer, including error
  shapes, empty pages, nulls, enums, defaults, dates/timezones, and unknown
  fields?
- Do callers and payloads that existed before the change still work?
- Do search, filters, sort, page totals, and exports agree between client and
  server?
- Are retry and timeout assumptions the same on both sides?

Never promote a contract claim to P0/P1 without reading both sides; when the
peer is unavailable, record a Coverage Gap.

## ui-runtime

Components, routes, forms, UI state, browser APIs, frontend data loading.

- Drive the changed flow in the running app from its user entry point. Does it
  reach the intended end state?
- Do loading, empty, error, permission, and stale-data states render and
  recover?
- Does navigation, refresh, or back/forward lose or duplicate state?
- Does the UI assume a field, shape, or status the API does not return?

Use the repository's browser harness or a `verify-<app>` skill; capture an
accessibility snapshot or screenshot as evidence.

## Maintainability

Maintainability results are reported only when they cite a documented
repository rule (`rule_anchor`: AGENTS.md, CLAUDE.md, CONTRIBUTING, ADR, lint
config) or show a concrete cost in this repository (for example, an existing
helper the change duplicates, with its anchor). Opinions about structure,
naming, or future extensibility are dropped. When the user explicitly asks for
a structural or maintainability review, also load
[solid-checklist.md](solid-checklist.md) and
[code-quality-checklist.md](code-quality-checklist.md), and the Thermo skill
when it is installed.
