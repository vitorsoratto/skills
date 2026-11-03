# Proof Protocol

Trident spends its budget running code, not arguing about it. A claim becomes a
finding only when the real code, at the reviewed head, behaves the way the
claim predicts. This file defines how a claim is proven, how a feature is
proven to work, how proofs are replayed, and what is never reported.

Why: LLM critics that only read code produce mostly unactionable comments, and
reading-only self-verification or debate does not reliably remove false
positives. Execution feedback does. See [evidence-basis.md](evidence-basis.md).

## Proof Levels

Every result and every Behavior Proof records how far its central fact was
pushed. Push it as far as is cheap and say where it stopped.

| Level | Meaning | Can block a PR? |
|---|---|---|
| `asserted` | The reviewer said so. | Never |
| `anchored` | A real `path:line` (or library source at the pinned version) shows it. | Never |
| `traced` | The failing path was walked step by step from a real entry point, both sides of every contract read. | Only with a recorded `execution_blocked` reason and a confirming replay |
| `executed` | A script or test calls the real code and fails loud when the claim is true. | Yes, once replay confirms |
| `reproduced` | The wrong outcome was observed through the running app, job, CLI, or API entry point. | Yes, once replay confirms |

`scripts/review_state.py` enforces this at finalize:

- a blocking correctness result (P0-P2) whose proof is below the bar becomes
  `insufficient_evidence` and is rendered as an **Unproven risk**. Unproven
  risks never request changes and never let the review approve;
- a P3 that was never run or traced is dropped (`rejected`): unexecuted
  non-blocking claims are noise;
- any result whose replay state is `mismatch` or `rejected` is dropped: the
  experiment contradicted it;
- a maintainability result with neither a `rule_anchor` nor source evidence of
  a concrete cost is dropped; a blocker without a rule becomes `major`.

### Allowed execution blockers

A proof may stop at `traced` only when `execution_blocked` is one of:

| Reason | Meaning |
|---|---|
| `untrusted_fork_code` | the Execution Trust Gate forbids running this PR |
| `missing_runtime: <what>` | the language runtime, emulator, or browser is not installable here |
| `missing_dependency: <what>` | a required service or package cannot be installed or started locally |
| `external_service: <what>` | the path needs a third-party system with no sandbox or recorded fixture |
| `requires_credentials: <what>` | the path needs credentials the review must not use |
| `requires_hardware: <what>` | the path needs a device or sensor |
| `no_disposable_data: <what>` | the only data that reaches the path is production or shared data |

Effort, complexity, confidence in reading, or time are not blockers. A traced
claim with any other reason is treated as unproven.

## Proof Recipe

A recipe is the runnable form of a proof, written so another agent can rerun it
cold:

```yaml
proof:
  level: executed
  recipe:
    files:            # new files only; never overwrite repository files
      - source: cor-1/redelivery.test.ts          # under $RUN_DIR/proofs
        dest: src/billing/__trident__/redelivery.test.ts
    setup: ["npm ci --prefer-offline --no-audit"]  # repository-native only
    command: "npx vitest run src/billing/__trident__/redelivery.test.ts"
    cwd: "."
    timeout_seconds: 300
    expect:
      head: fail      # pass | fail | skip
      base: pass      # differential: did the change introduce it?
      failure_signature: "charged 2 times"   # regex; the failure must be the claimed one
  execution_blocked: null   # required reason when level is traced
  replay: {state: confirmed, differential: introduced_by_change}
```

Recipe rules:

1. Exercise the real code path named in the claim. Mock only at a boundary the
   production code already isolates (network, clock, third-party API). Never
   mock the unit under suspicion.
2. Assert the observable outcome a user, job, or caller would see: the stored
   row, the HTTP status and body, the emitted event, the rendered state.
3. Write a `failure_signature` specific to the claimed wrong outcome. A test
   that fails on an import error, a missing dependency, or a timeout does not
   prove the claim.
4. Prefer the repository's test runner and fixtures, so the proof can become a
   regression test in Trident Fix. Keep proof files under a `__trident__/`
   directory or a `trident_proof` name so they are obviously temporary.
5. For a regression claim, set `expect.base` so replay shows whether the change
   introduced it (`introduced_by_change`) or it was already there
   (`preexisting`). Preexisting bugs are reported as non-blocking context unless
   the change makes them reachable or worse.

## Behavior Proofs: prove the change works

Bug hunting is half the job. The other half is proving the new behavior works
end to end, inside the **Impact Set** only (see
[system-map.md](system-map.md)). Every review proves, for each affected flow,
and for one representative of each equivalence class:

- **Essential path**: drive the flow from its real entry point (route, command,
  job, screen, public function) through the changed code to its sink (storage,
  response, event, rendered state), and observe the intended result.
- **Acceptance criteria**: when a Requirement Source exists, each mandatory
  criterion maps to at least one Behavior Proof.
- **Required proofs** from the Review Plan (`required_proofs` from
  `scripts/triage_policy.py`), such as `retry-idempotency` or
  `authz-negative-matrix`.
- **Stress profile** from the Review Plan, applied to the riskiest flow:

| Stress | What to run |
|---|---|
| `boundary` | Empty, null, limit, off-by-one, ordering, unicode, timezone, and malformed inputs for each changed function or endpoint; prefer property-based tests when the repo has a library. |
| `repetition` | Run the same operation twice and N times: redelivery, retry, double submit, re-run of a job, re-applied migration. |
| `concurrency` | Run N concurrent executions against shared state and check the invariant (counts, uniqueness, balances, ordering). |
| `failure-injection` | Make one dependency fail, time out, or return partial data mid-operation; check rollback, retry, and the user-visible error. |
| `volume` | Run with a realistic large input or page count; check limits, pagination totals, memory, and timeouts. |

The stress profile arrives from the Review Plan as one Behavior Proof per
kind (`stress-boundary`, `stress-repetition`, ...), so each kind gets its own
disposition and evidence.

Each Behavior Proof records `proof_id`, `flow`, `disposition`
(`executed|satisfied_by_ci|not_applicable|not_checked|blocked`), `outcome`
(`held|failed|null`), `evidence` (command plus a short output excerpt or
artifact path), `approval_critical`, and `affected_paths`. Disposition rules,
enforced by `scripts/review_state.py` and `scripts/stage_gate.py`:

- `executed` requires `evidence`; without it the proof reverts to `not_checked`;
- `blocked` and `not_applicable` require `reason`;
- `affected-flow-e2e` and `existing-tests-at-head` are never `not_applicable`;
  when they cannot run, use `blocked` with an allowed execution blocker;
- `not_checked` is a planning state only; at finalize it blocks completion and
  the review ends in `no_verdict`.

A failed Behavior Proof becomes a correctness result with the same recipe as
its proof and `behavior_proof_id` set to the proof; a failed proof without a
result blocks completion. An approval-critical proof that is `blocked` becomes
an Unproven risk and prevents approval.

For concurrency, ordering, or state-machine changes where tests cannot
enumerate interleavings, use the repository's model checker or formal spec when
one exists (TLA+, P, Alloy, Kani, Dafny) and show the check failing on a broken
variant first. Do not invent a formal model during a review; record a Coverage
Gap that recommends one.

## Replay: independent verification by execution

Replay replaces reading-based verification and the old judge stage.

1. Create fresh detached worktrees at the reviewed head and, for differential
   recipes, at the base. Never reuse a prover's worktree.
2. A fresh Replay agent receives only each claim, its anchors, and its recipe,
   not the prover's reasoning. It is always a separate agent: neither the
   orchestrator nor a Prover replays. It audits each recipe against the rules
   above (real path, no mocked suspect, assertion matches the claim, specific
   signature) and rejects recipes that fail the audit. It runs even with zero
   claims, rerunning `affected-flow-e2e` and `existing-tests-at-head` from
   their recorded commands, and sets `verification.independent: true`.
3. Run every surviving recipe:

   ```bash
   python3 scripts/replay_proofs.py --proofs "$RUN_DIR/proofs.json" \
     --proof-root "$RUN_DIR/proofs" --head-worktree "$RUN_DIR/replay-head" \
     [--base-worktree "$RUN_DIR/replay-base"]
   ```

   The script refuses branch checkouts, refuses to overwrite files, removes the
   files it added, records leftover worktree changes, and exits `2` when any
   recipe does not behave as predicted.
4. Copy each replay result into `proof.replay` (`confirmed`, `mismatch`,
   `blocked`, plus `differential`). Only `confirmed` keeps a blocking result.
   A `mismatch` is rejected unless the prover can explain it with a new recipe
   that replay then confirms; one retry at most.
5. For `traced` proofs, the Replay agent re-traces the path independently from
   the entry point and records `confirmed` or `rejected`.

Disagreements are settled by running a discriminating experiment, never by
another round of argument. When no experiment is possible, the result is
`insufficient_evidence`.

## Execution safety

Executing code is the point, so the limits are strict:

- **Trust gate.** Execute PR code only when `execution_trust.same_repository`
  is true, the mode is local, or the user explicitly allows executing a
  cross-repository (fork) PR. Otherwise every proof is `blocked` with reason
  `untrusted_fork_code`, and Trident falls back to `traced` proofs.
- Run only inside Trident's disposable detached worktrees under `$RUN_DIR`,
  never in the user's checkout.
- Use disposable data only: test databases, containers, temp directories, and
  seeded fixtures the repository provides. Never connect to production, shared
  staging, or real third-party accounts; never send real email, SMS, payments,
  or webhooks.
- Never run deploy, publish, release, push, or migration commands against
  anything but a disposable target. Never print secrets, tokens, or connection
  strings into evidence.
- Every command has a timeout. Kill only processes this run started, by PID;
  never by name or pattern.
- Cleanup removes worktrees, containers, and scratch state, but keeps proof
  artifacts under `$RUN_DIR/artifacts` until the review is rendered.

## Signal policy: what is not a finding

Drop these before proving anything. They cost tokens and bury real bugs:

- style, naming, formatting, and comment wording, unless a documented
  repository rule says otherwise (cite it in `rule_anchor`);
- "consider adding tests" without a concrete behavior that fails;
- defensive checks for states the System Map shows cannot occur;
- hypothetical future callers, configurations, or scale ("YAGNI risks");
- alternative designs that are not demonstrably wrong for this repository;
- anything you did not run or trace to a concrete wrong outcome.

"No findings" is a valid result when the Behavior Proofs hold. Report the same
root cause once, with every location. Keep each finding short and attach the
code and the proof command.
