# Removal Gate Evidence Matrix

Removal is a downstream decision, not a broad dead-code scan and not a
correctness severity. A candidate is safe only after all applicable evidence is
collected and independently verified.

## Candidate record

Use the canonical envelope with:

- `axis: removal` and `kind: removal_candidate`;
- `classification: safe|defer|insufficient|not_removable`;
- a relevant path, symbol, and line anchor;
- current behavior, trigger, expected behavior, impact, constraints, and
  bounded next action;
- `evidence` entries for every reachability check and exact verification command.

## Required reachability checks

- direct references and imports/exports;
- routes, jobs, dependency injection, registration, configuration, and generated
  registries;
- tests, fixtures, snapshots, documentation, examples, and migrations;
- dynamic/reflection use, string-based lookup, feature flags, and telemetry;
- public API/SDK consumers and relevant history;
- base-snapshot comparison for deleted paths;
- focused tests or package checks that prove the preserved behavior.

## Outcomes

| Classification | Meaning |
|---|---|
| `safe` | Reachability and impact evidence supports removal and verification is recorded. |
| `defer` | A consumer, migration, telemetry window, or owner decision remains. |
| `insufficient` | Evidence is missing or a tool/check is blocked. |
| `not_removable` | The candidate is reachable, externally owned, or removal violates a constraint. |

Never call code safe from a text search alone. Do not prescribe an unrelated
refactor. The final Remediation Report includes dependencies, rollback or
migration preconditions, and the exact discovered checks.
