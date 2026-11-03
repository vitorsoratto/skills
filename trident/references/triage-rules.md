# Deterministic Triage Rules

The collector supplies facts; these rules produce the minimum Risk Map and
Review Plan. The same evidence must produce the same minimum plan. A model may
escalate with a short reason but may not remove a required capability or check.

## Signal-to-capability rules

Capabilities select the [risk questions](risk-questions.md) the Prover loads
and the Behavior Proofs it must run. They do not create reviewer agents.

| Evidence signal | Risk dimensions | Capability (question bank) | Required Behavior Proofs |
|---|---|---|---|
| auth, authorization, tenant, secret, trust boundary, URL/file/input handling, crypto | correctness, contract, runtime | `security-trust` | `authz-negative-matrix`, `hostile-input` |
| schema, migration, persistence, transaction, concurrency, cache, queue, retry, billing | correctness, contract, runtime | `data-integrity` | `persistence-readback`, `retry-idempotency`, `concurrency-invariant`; `migration-forward-rollback` for migrations |
| public API, DTO, event, webhook, SDK, integration, serialization, pagination, cross-module call | contract, correctness | `contract-integration` | `producer-consumer-roundtrip`, `compat-previous-shape` |
| component, route, form, UI state, browser API, frontend data loading | runtime, contract | `ui-runtime` | `drive-changed-flow`, `ui-state-matrix` |
| changed function/handler/validator/parser/mapper or feature logic | correctness | `edge-functions` | `boundary-properties` |
| any source change | correctness, evidence | always | `affected-flow-e2e`, `existing-tests-at-head` |
| new abstraction/layer/dispatcher/state machine, central boundary, refactor intent, file >1000 lines, branch-mode growth | structural, correctness | Thermo Gate (`thermo`), when installed | structural maintainability review; focused regression check |
| deletion, deprecation, feature-flag cleanup, branch pruning | correctness, structural, evidence | `removal-dead-code` / Removal Gate | reachability and impact matrix; build and related tests at head |
| valid issue/PRD/spec or implementation-bound ADR | requirement | `spec-alignment` | one Behavior Proof per mandatory acceptance criterion |

`scripts/triage_policy.py` emits these as `required_proofs`. Proofs for
`auth_trust`, `persistence_data`, and `migrations` are `approval_critical`, as
is `affected-flow-e2e` once correctness risk is `medium` or higher.

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

## Stress profile

The correctness risk level selects the stress the Prover applies to the
riskiest affected flow (see [proof-protocol.md](proof-protocol.md)):

| Correctness risk | Stress profile |
|---|---|
| low | none beyond the essential path |
| medium | `boundary` |
| high | `boundary`, `repetition`, `concurrency` |
| critical | `boundary`, `repetition`, `concurrency`, `failure-injection`, `volume` |

## Depth and budgets

Tokens go to running code. Agent counts stay small.

| Plan | Minimum topology | Agent budget |
|---|---|---:|
| baseline | orchestrator builds context; one Prover; one Replay agent | 2 |
| escalated | + up to two more Provers in parallel, split by affected flow | 4 |
| deep | + Context Mapper agent, base-differential replay for every result, up to four Provers | 6 |

Split Provers by affected flow, keeping each near 400 changed lines or 20
files; never by "persona". Each Prover gets its own detached worktree.
Explicit `quick`/`deep` requests set the requested ceiling, subject to required
minimums. Ordinary PRs with no risk signal remain baseline even when GitHub
metadata is available.

## Check dispositions and CI

For each required check and Behavior Proof, declare one of `executed`, `satisfied_by_ci`,
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
