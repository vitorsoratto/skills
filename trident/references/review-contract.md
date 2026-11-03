# Review Contract

The canonical result envelope is defined in [output-contract.md](output-contract.md).
The proof rules are defined in [proof-protocol.md](proof-protocol.md). This
reference defines the gates and cross-stage obligations the envelope records.

## Core chain

`Triage -> Context -> Prove -> Replay -> Finalize -> Render` is the required
ordering.

- **Context** refreshes the System Map and writes the Change Context Brief
  before any hypothesis is formed.
- **Prove** runs Behavior Proofs for the affected flows and turns suspicions
  into Proof Recipes. Provers emit provisional results only.
- **Replay** re-runs every recipe in fresh worktrees without the prover's
  reasoning. It is the only verification stage. There is no judge or debate
  stage: disagreements are settled by a discriminating run, or the result is
  `insufficient_evidence`.
- **Finalize** applies the proof gate, IDs, completion, and verdict through
  `scripts/review_state.py finalize`.

## Required gates

- Correctness and Behavior Proofs always run for source changes.
- Maintainability results require a `rule_anchor` to block.
- Spec Alignment runs only when the Spec Gate finds a valid Requirement Source;
  its mandatory criteria map to Behavior Proofs.
- Removal runs only for a changed deletion/deprecation or a concrete Removal
  Candidate.
- The Execution Trust Gate decides whether PR code may run (same-repository
  PR, local mode, or explicit user permission for a fork).
- Current CI may satisfy an applicable check only when it belongs to the exact
  reviewed head. Configuration discovery is `configured`, never `enforced`.
- Every planned check and every required Behavior Proof gets exactly one
  disposition.

## Evidence obligations

Every blocking result needs a complete Evidence Packet whose proof meets the
bar in [proof-protocol.md](proof-protocol.md) and was confirmed by Replay.
Replay preserves the original axis and kind and records `rejected` or
`insufficient_evidence` when a claim fails.

Removal requires reachability evidence across direct references, exports,
routes/jobs/DI/config, tests/docs, dynamic or reflection use, external
consumers, telemetry when applicable, and relevant history. Text search alone
cannot yield `safe`.

## Freshness and cleanup

Capture the reviewed head before dispatch. Re-read it before rendering. If it
moved, compute the old-to-new delta, rebuild affected manifest entries, and
rerun invalidated proofs and checks. After two refreshes, stop with
`review_superseded`. Cleanup of detached worktrees, started processes,
containers, and temporary state is a completion requirement. The System Map
cache and the rendered review are the only state that outlives the run.
