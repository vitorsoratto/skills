# Deterministic Triage Rules

The collector supplies facts; these rules produce the minimum Risk Map and
Review Plan. The same evidence must produce the same minimum plan. A model may
escalate with a short reason but may not remove a required capability or check.

## Signal-to-capability rules

| Evidence signal | Risk dimensions | Minimum capability/lane | Required checks |
|---|---|---|---|
| auth, authorization, tenant, secret, trust boundary, URL/file/input handling, crypto | correctness, contract, runtime | `security-trust` | focused auth/input test; peer policy/config check |
| schema, migration, persistence, transaction, concurrency, cache, queue, retry, billing | correctness, contract, runtime | `data-integrity` | migration/rollback or focused persistence test; retry/idempotency check |
| public API, DTO, event, webhook, SDK, integration, serialization, pagination, cross-module call | contract, correctness | `contract-integration` | producer/consumer contract check; focused integration test |
| component, route, form, UI state, browser API, frontend data loading | runtime, contract | `ui-runtime` | focused render/interaction check; loading/error/empty-state check |
| changed function/handler/validator/parser/mapper or feature logic | correctness | `edge-functions` | essential path plus relevant boundary check |
| new abstraction/layer/dispatcher/state machine, central boundary, refactor intent, file >1000 lines, branch-mode growth, 2 related structural signals | structural, correctness | Thermo Gate (`thermo`) | structural maintainability review; focused regression check |
| deletion, deprecation, feature-flag cleanup, branch pruning, deletion-oriented simplification | correctness, structural, evidence | `removal-dead-code` / Removal Gate | reachability and impact matrix; tests/docs/config/history check |
| valid issue/PRD/spec or implementation-bound ADR | requirement | `spec-alignment` | requirement coverage matrix |
| behavioral source change without changed tests or CI test evidence | evidence, correctness | focused test verification | affected test/script discovery; test or explicit blocked disposition |

Signals are objective when derived from changed paths, repository metadata,
manifest content, discovered references, or explicit PR metadata. Do not infer
security or UI capability from file size alone.

## Risk Map

Record one level per dimension: `low`, `medium`, `high`, or `critical`.

| Evidence | Scope | Correctness | Contract | Structural | Runtime | Requirement | Evidence | PR state |
|---|---|---|---|---|---|---|---|---|
| <=10 source lines, one package, no boundary signal | low | low | low | low | low | low | medium if no CI | low |
| 11–100 lines, multiple files or one boundary signal | medium | medium | medium | medium | medium | medium | medium | medium |
| >100 lines, multiple packages, generated/migration/deletion, or 2+ signals | high | high | high | high | high | high | high | medium |
| auth/data loss/security, unresolved required check, contradictory evidence, stale PR head | high | critical | critical | high | critical | high | critical | critical |

The table is a floor: a critical signal in one dimension does not deepen
unrelated dimensions. `pr` mode alone is not a deep signal.

## Depth and budgets

| Plan | Minimum topology | Budget |
|---|---|---:|
| baseline | shared Scanner + shared Verifier | 2 |
| escalated | baseline + required specialist lanes or Thermo/Spec/Removal | 4 |
| deep | escalated + independent specialist verification and conditional Arbiter | 6 |

Explicit `quick`/`deep` requests set the requested ceiling, subject to required
minimums. Ordinary PRs with no risk signal remain baseline even when GitHub
metadata is available. Compatible capabilities may share the Scanner, but every
required capability must be represented in the plan and must pass through the
Verifier.

## Check dispositions and CI

For each required check, declare one of `executed`, `satisfied_by_ci`,
`not_applicable`, `not_checked`, or `blocked`. `satisfied_by_ci` requires exact
head identity and a successful check result. If CI is absent, use the affected
package's discovered native script; if no authoritative command exists, record
`blocked` or `not_checked` and a Coverage Gap. Never treat a configured workflow
as proof that it ran.

## Coverage Manifest

Account for every changed path without truncation. Use these classes and
treatments:

| Class | Treatment |
|---|---|
| source | semantic review and focused verification |
| generated | inspect generator/provenance and generation check |
| lockfile | manifest intent and dependency-risk check |
| snapshot | originating behavior/test check |
| vendored | provenance, version, checksum |
| binary | metadata, size, intent; content is unsupported |
| deleted | base snapshot plus Removal Gate |
| renamed | separate movement from semantic edits |
