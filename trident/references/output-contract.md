# Canonical Trident Result Contract

All stages consume and emit the same envelope. This file is the single source
of truth for result shape, classifications, lifecycle state, and rendering.
Prompts may add stage-owned observations, but they must not redefine this
schema or invent another finding ID namespace.

## Envelope

```yaml
schema_version: trident-result-v1
stage: triage|context|prover|spec-alignment|removal-dead-code|thermo|replay|completion|render
review_snapshot:
  mode: pr|range|unstaged|staged|all-local|dir
  base_sha: string|null
  head_sha: string|null
  merge_base: string|null
  current: true|false|unknown
  refresh_count: integer
review_plan:
  depth_by_axis:
    correctness: baseline|escalated|deep
    maintainability: baseline|thermo-depth|deep
    spec_alignment: skipped|baseline|deep
  active_capabilities: [string]
  budget: baseline|escalated|deep
  required_checks: [string]
  required_proofs: [string]
  stress_profile: [boundary|repetition|concurrency|failure-injection|volume]
  escalation_reason: string|null
system_context:
  map_location: string|null
  refreshed_sections: [string]
  change_context_brief: string|null
  safety_facts: [{fact, proof_id, level}]
  affected_flows: [{flow, entry_point, sink, changed_symbols: [string]}]
  impact_set:
    equivalence_classes: [{representative, members: [string], shared_property}]
    dismissed_usages: [{path, symbol, reason}]
behavior_proofs:
  - proof_id: string
    flow: string|null
    goal: string
    disposition: executed|satisfied_by_ci|not_applicable|not_checked|blocked
    outcome: held|failed|null
    approval_critical: true|false
    affected_paths: [string]
    evidence: string|null
    reason: string|null
coverage_manifest:
  status: complete|partial|blocked
  entries: [{path, status, class, treatment, additions, deletions}]
triage_evidence: object|null
check_dispositions:
  - check_id: string
    required: true|false
    disposition: executed|satisfied_by_ci|not_applicable|not_checked|blocked
    evidence: [string]
verification:
  state: provisional|verified|rejected|insufficient_evidence|blocked|not_checked
  independent: true|false
  current_source: observed|inferred|blocked|not_checked
  reason: string|null
results:
  - id: null|COR-1|MNT-1|SPEC-1|REM-1
    axis: correctness|maintainability|spec_alignment|removal|coverage_gap
    kind: correctness_bug|maintainability_concern|spec_requirement|removal_candidate|coverage_gap
    classification: P0|P1|P2|P3|blocker|major|advisory|missing|partial|wrong|scope_creep|safe|defer|insufficient|not_removable|null
    requirement_importance: mandatory|important|nice_to_have|null
    status: provisional|verified|rejected|insufficient_evidence
    title: string
    location: {path, symbol, start_line, end_line, changed_line, precise}
    placement: inline|summary
    claim: string
    trigger: string
    impact: string
    evidence: [{path, line, fact, source: observed|inferred|blocked|not_checked}]
    confidence: high|medium|low
    correction_direction: string|null
    verification_guidance: [string]
    dependencies: [string]
    evidence_packet: object|null
    cross_references: [string]
    origin_stage: string
    rule_anchor: string|null            # required for a maintainability blocker
    proof:
      level: asserted|anchored|traced|executed|reproduced
      recipe: {files: [{source, dest}], setup: [string], command, cwd, timeout_seconds,
               expect: {head: pass|fail|skip, base: pass|fail|skip, failure_signature}}
      execution_blocked: string|null
      observed: {head: string|null, base: string|null}
      replay: {state: confirmed|mismatch|blocked|rejected, differential: introduced_by_change|preexisting|confirmed_head_only|behavior_holds|null}
    proof_gate: string|null             # set by review_state.py when a blocker is downgraded
coverage_gaps:
  - id: null|GAP-1
    area: string
    reason: string
    effect_on_confidence: string
    disposition: blocked|not_checked|insufficient_evidence
review_completion:
  status: complete|partial|blocked|review_superseded
  current_snapshot: true|false
  manifest_complete: true|false
  gates_resolved: true|false
  checks_resolved: true|false
  results_verified: true|false
  cleanup_verified: true|false
  blockers: [string]
unproven_risks: [{kind: unproven_claim|unproven_behavior, title, severity, reason, path}]
review_verdict: approve|request_changes|comment|no_verdict|null
render:
  developer_review: string|null
  remediation_markdown: string|null
```

Fields may be `null` before their owning stage runs. A final envelope must
populate every field that is relevant to its Review Plan and must preserve
blocked or insufficient evidence instead of converting it into a finding.

## Axes and classifications

The axes are independent and are never reranked against one another:

| Axis | Kind | Classification | ID prefix |
|---|---|---|---|
| Correctness | `correctness_bug` | `P0`, `P1`, `P2`, `P3` | `COR-*` |
| Maintainability | `maintainability_concern` | `blocker`, `major`, `advisory` | `MNT-*` |
| Spec Alignment | `spec_requirement` | `missing`, `partial`, `wrong`, `scope_creep` plus importance | `SPEC-*` |
| Removal | `removal_candidate` | `safe`, `defer`, `insufficient`, `not_removable` | `REM-*` |
| Coverage | `coverage_gap` | no severity or priority | no finding ID required |

`P0`–`P3` is valid only when `axis: correctness`. A spec gap is not a
correctness bug merely because it blocks approval. A Removal result is a
decision about reachability, not a claim that code is dead.

## Evidence Packet, proof, and verification

Every blocking result (`COR-P0/P1/P2`, `MNT-blocker`, or mandatory
`SPEC-missing/wrong`) requires an `evidence_packet` containing:

- the claim and reachable trigger;
- concrete user, production, data, or delivery impact;
- source evidence with file and line anchors;
- the `proof` with its level, recipe, and replay outcome;
- bounded correction direction preserving repository constraints;
- exact correction verification guidance (normally: rerun the Proof Recipe and
  see it flip from fail to pass).

The proof bar is defined in [proof-protocol.md](proof-protocol.md) and
enforced by `scripts/review_state.py`:

- blocking correctness needs `proof.level` `executed` or `reproduced` with
  `proof.replay.state: confirmed`, or `traced` with `execution_blocked` and a
  confirming replay;
- a maintainability blocker needs a `rule_anchor`; without one it becomes
  `major`;
- results that miss the bar become `insufficient_evidence`, keep their audit
  trail, and appear in `unproven_risks` instead of `results`.

Replay may set `rejected` or `insufficient_evidence`; those outcomes remain
auditable but are not findings. Results receive stable IDs only after
same-axis/same-kind deduplication and replay. Cross-axis related results
retain separate IDs and reference one another through `cross_references`.

## Completion, verdict, and placement

`complete` requires a current snapshot, exhaustive manifest, resolved required
gates, one disposition for every planned check, verified results, and cleanup.
`partial`, `blocked`, and `review_superseded` can report useful evidence but
always produce `no_verdict`. A moving PR head may be refreshed twice; further
movement produces `review_superseded`.

The Approval Gate requires `complete`, current source, no blocking correctness
result, no maintainability blocker, no mandatory missing/wrong requirement, no
required check with `blocked` or `not_checked` disposition, no failed Behavior
Proof, and no Unproven risk (an unproven severe claim or an approval-critical
Behavior Proof that is `blocked` or `not_checked`). Only then may the verdict be
`approve`; blocking verified results yield `request_changes`, and complete
reviews with only non-blocking results or Unproven risks yield `comment`.

Use `inline` only for a precise useful changed-line anchor. Architecture,
cross-file, deleted-line, requirement, coverage, and review-state results use
`summary` placement.

## Rendering

The Developer Review contains the verdict/current head, blockers with their
proof line, Unproven risks, the Behavior Proofs that ran, and the check
summary. P3, advisories, coverage gaps, and supporting evidence belong under a
collapsed `<details>` section. When at least one verified result exists, also
render one Remediation Markdown report using the same stable IDs. The report
must include anchors, current/expected behavior, impact, constraints, bounded
fix direction, the Proof Recipe, exact discovered checks, dependencies, and the
full Evidence Packet, without private chain-of-thought. Render both views with
`python3 scripts/review_state.py finalize --input envelope.json`. Do not emit a parallel JSON report
or write into the reviewed repository unless the Artifact Persistence Gate is
explicitly opened with a destination.
