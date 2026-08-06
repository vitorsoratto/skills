# Review Contract

The canonical result envelope is defined in [output-contract.md](output-contract.md).
This reference defines the gates and cross-stage obligations that the envelope
records.

## Core chain

`Triage -> Scan -> Verify -> Judge -> Complete -> Render` is the required
ordering. Review Lenses produce provisional axis-specific results and Coverage
Gaps; they never bypass the Verifier. The Arbiter is conditional and is never a
substitute for independent verification.

## Required gates

- Correctness always runs.
- Maintainability runs at baseline and escalates through the Thermo Gate.
- Spec Alignment runs only when the Spec Gate finds a valid Requirement Source.
- Removal runs only for a changed deletion/deprecation or a concrete Removal
  Candidate.
- Current CI may satisfy an applicable check only when it belongs to the exact
  reviewed head. Configuration discovery is `configured`, never `enforced`.
- Missing Current CI activates the Local Verification Fallback; focused
  repository-native checks take precedence over a full suite.
- Every planned check gets exactly one Check Disposition.

## Evidence obligations

Every blocking result needs a complete Evidence Packet. The Verifier must
independently re-read current source, preserve the original axis and kind, and
explicitly record `rejected` or `insufficient_evidence` when a claim fails.
The Arbiter is required only for P0/P1 results, disputes, insufficient evidence
that matters to the verdict, high-risk structural blockers, or contradictory
required evidence.

Removal requires reachability evidence across direct references, exports,
routes/jobs/DI/config, tests/docs, dynamic or reflection use, external
consumers, telemetry when applicable, and relevant history. Text search alone
cannot yield `safe`.

## Freshness and cleanup

Capture the reviewed head before dispatch. Re-read it before rendering. If it
moved, compute the old-to-new delta, rebuild affected manifest entries, and
rerun invalidated lanes/checks. After two refreshes, stop with
`review_superseded`. Cleanup of detached worktrees and temporary state is a
completion requirement, not an optional note.
