---
name: trident-fix
description: "Fix and push the verified findings from the immediately preceding Trident PR review."
disable-model-invocation: true
---

# Trident Fix

Resolve the reviewed snapshot, not a nearby branch or a remembered version.

**Iron law:** every implementation path ends on the reviewed PR's existing head
branch, pushed and confirmed at the remote head.

## Workflow

```
Trident Fix:
- [ ] Resolve the review and PR head
- [ ] Route to the current or a fresh context
- [ ] Revalidate and order every finding
- [ ] Implement root fixes
- [ ] Exercise changed behavior
- [ ] Commit, push, and confirm the remote head
```

## 1. Resolve the remediation set

Take the Developer Review and Remediation Markdown from the immediately
preceding Trident run. Require a GitHub PR identity, reviewed head SHA, stable
finding IDs, and the complete handoff fields: anchors, current and expected
behavior, impact, constraints, bounded correction direction, discovered checks,
dependencies, and Evidence Packets.

Resolve the PR's current metadata, head repository/owner, existing head branch,
and exact push remote/refspec from GitHub. Compare its remote head with the
reviewed SHA. When they differ, inspect the delta and revalidate affected
findings before routing. Stop as blocked when the reviewed state or push target
cannot be reconstructed safely. A local branch with a similar name is not
identity evidence.

The remediation set is every verified actionable finding unless the user
explicitly excluded an ID. Rejected, insufficient, and coverage-gap claims are
not implementation work. When the set is empty, report that no commit or push
was needed.

**Completion:** the PR, current remote head, head repository/owner, branch,
push target, and remediation set are explicit; every included ID has a complete
handoff or is blocked by a named missing field.

## 2. Route by context

Use the **current context** only when all are true:

- at most three actionable findings;
- one package or tightly coupled subsystem;
- no dependency ordering between findings;
- the review and unrelated conversation leave enough context to re-read the
  affected code and verify each claim without compressing evidence away.

Use a **fresh context** when any are true:

- four or more actionable findings;
- findings cross packages, services, or architectural boundaries;
- one fix depends on another;
- the review or preceding conversation is context-heavy;
- confidence in the current context's evidence retention is uncertain.

These rules cover three branches: a small local review stays in this chat; a
large or cross-cutting review moves to a fresh context; a small review also
moves when context pressure is high. Route uncertainty to a fresh context.

For a fresh context, dispatch one implementation executor with only:

1. PR URL/number, base repository and branch, head repository/owner and branch,
   exact push remote/refspec, reviewed SHA, and current remote head;
2. the complete Remediation Markdown, preserving stable IDs and dependencies;
3. repository constraints and exact checks discovered by Trident;
4. the mandate to re-resolve GitHub metadata, revalidate every finding against
   the current head, implement all still-valid findings, commit, push to the
   existing PR branch, and return the delivery record below.

Exclude the original review transcript, discarded claims, and private
reasoning. The fresh executor owns the remaining workflow end to end. Treat this
invocation as authorization to implement and push; add no approval pause.

**Completion:** exactly one executor owns implementation, and a fresh executor
has enough evidence to proceed without repeating the review.

## 3. Revalidate and order

Check out the PR's existing head branch and synchronize it without rewriting
history. Confirm the working tree will not overwrite unrelated user work. Before
editing each ID, re-read its anchors and reproduce the reported behavior on the
current head. When the Remediation Report carries a Proof Recipe, rerun that
recipe first: it must fail with its failure signature now and pass after the
fix. Keep it as the regression test when it fits the repository's test layout.
Mark stale or disproven findings with
evidence instead of forcing a change.

Order valid findings by declared dependencies, then shared root cause. Define
the smallest observable behavior that proves each correction. Use Trident's
discovered repository-native checks; discover a replacement only when the
original command is stale, and record why.

**Completion:** every ID is `valid`, `stale`, `disproven`, or `blocked`; valid
IDs have an execution order and a behavioral proof.

## 4. Fix and verify

Fix the root cause while preserving each finding's constraints. Migrate affected
callers and remove obsolete paths created by the fix. Keep unrelated cleanup out
of the diff.

After each dependency group, run the narrow behavioral reproduction. Then run
the applicable discovered focused tests and affected-package checks. A command
passing without exercising the changed contract is not proof. Delivery requires
passing behavioral proofs and applicable checks. Treat a non-passing check as
blocked only with evidence that it is unrelated or environmental; no
remediation-caused failure may remain. If a valid finding cannot be completed,
finish independent findings and report the exact blocker; do not represent
partial remediation as complete.

**Completion:** every valid unblocked ID is fixed, its original failure no
longer reproduces, and applicable focused checks pass or have an evidenced,
reported blocker unrelated to the remediation.

## 5. Deliver to the PR branch

Refresh the remote PR head immediately before delivery. If it moved, integrate
the new head normally and rerun invalidated proofs. Create no empty commit.
Commit the scoped remediation and push the current commit through the resolved
remote/refspec matching the PR's head repository and head branch. Use a normal
push; preserve remote history. Confirm through GitHub that the PR head SHA
equals the pushed commit.

Return:

```text
PR: <url or number>
Branch: <existing PR head branch>
Findings: <ID -> fixed | stale | disproven | blocked>
Checks: <command/scenario -> result>
Commit: <SHA or "none">
Push: <confirmed remote SHA or "not needed">
Blockers: <exact blockers or "none">
```

When campaign metadata came from `trident-converge`, also return the same record
as delivery JSON keyed by each ledger `campaign_key` (`TC-*`); include the
current Trident ID inside the value as metadata. Hand control back to that skill.
The campaign's deterministic decision is the sole authority for another
correction cycle.

**Completion:** every finding is accounted for, every claimed fix has behavioral
evidence, and either the pushed commit is the confirmed remote PR head or
revalidation left no valid unblocked code change and explains why no push was
needed.

## Guardrails

- Preserve the PR's existing head branch; branch substitution breaks the
  handoff.
- Preserve remote history with normal synchronization and push.
- Make code changes only for revalidated findings and their required callers.
- Use repository evidence for commands; record blocked checks rather than
  inventing substitutes.
- Keep stable Trident IDs through implementation, verification, and delivery.
