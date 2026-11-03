# Trident Review System

Trident is an execution-first code review process: it builds context about how the system works, proves the changed behavior by running it, and reports only claims an independent replay confirms, so conclusions stay traceable and resistant to false positives. Design evidence: references/evidence-basis.md.

## Language

**Review Snapshot**:
The immutable source state and comparison boundary against which every review claim is evaluated.
_Avoid_: Current code, latest diff, review target

**Core Chain**:
The fixed Context, Prove, and Replay sequence that turns suspicions into final review conclusions.
_Avoid_: Scan/Verify/Judge, reviewer debate

**System Map**:
The persistent per-repository record of flows, architecture, contracts, operations, and hazards, kept outside the repository and refreshed section by section when its anchors change.
_Avoid_: Repository summary, one-off context dump

**Change Context Brief**:
The per-review account of intent, affected flows, contracts on both sides, safety facts, existing coverage, and how to exercise each flow, built before any hypothesis.
_Avoid_: Diff summary, file list

**Impact Set**:
Every place the changed behavior can reach: confirmed usages of changed symbols, readers and writers of changed data, and the entry points above them; the only scope Trident tests.
_Avoid_: Whole codebase, changed files only

**Equivalence Class**:
Usages of a changed unit that share the same configuration and inputs, proven through one representative.
_Avoid_: Sampling at random

**Affected Flow**:
A path from a real entry point (route, command, job, screen, public API) through changed symbols to a sink (storage, response, event, rendered state).
_Avoid_: Changed file, touched function

**Safety Fact**:
One of the few facts a change is safe because of; each becomes a proof target.
_Avoid_: Assumption, general risk

**Risk Question**:
A capability-specific hypothesis prompt the Prover turns into a runnable prediction or drops.
_Avoid_: Review Lens, checklist item to report

**Proof Level**:
How far a claim's central fact was pushed: asserted, anchored, traced, executed, or reproduced.
_Avoid_: Confidence label

**Proof Recipe**:
The runnable form of a proof: files to add, setup, one command, and the expected outcome at head and base with a failure signature.
_Avoid_: Verification guidance prose

**Behavior Proof**:
Executed evidence that an Affected Flow, required proof, acceptance criterion, or stress case behaves as intended.
_Avoid_: Test suite passed, it compiles

**Stress Profile**:
The risk-selected set of boundary, repetition, concurrency, failure-injection, and volume runs applied to the riskiest Affected Flow.
_Avoid_: Load test by default

**Replay**:
Independent verification by re-running every Proof Recipe in fresh worktrees without the prover's reasoning.
_Avoid_: Verifier rereading code, Arbiter

**Differential Proof**:
A replay at both base and head that shows whether the change introduced a behavior or it was preexisting.
_Avoid_: Path overlap, blame guess

**Unproven Risk**:
A severe claim or approval-critical Behavior Proof that execution could not settle; it prevents approval without requesting changes.
_Avoid_: Finding, ignored suspicion

**Stage Gate**:
A mechanical check (`scripts/stage_gate.py context|plan|prove|replay`) that a stage's artifacts satisfy its completion criteria; an agent's statement that a stage is done does not count.
_Avoid_: Self-assessment, checklist tick

**Allowed Execution Blocker**:
One of the enumerated reasons a proof may stop at `traced` (untrusted fork code, missing runtime or dependency, external service, credentials, hardware, no disposable data); effort or confidence never qualifies.
_Avoid_: Too complex, obvious from reading

**Execution Trust Gate**:
The rule that PR code runs only for same-repository PRs, local modes, or forks the user explicitly allowed.
_Avoid_: Run everything, sandbox assumed

**Evidence Gate**:
A checkable condition that must pass before a claim can advance to a stronger status or severity.
_Avoid_: Heuristic, recommendation

**Coverage Manifest**:
The exhaustive inventory of files and source states included, excluded, or unsupported by a review.
_Avoid_: File sample, first files

**Coverage Class**:
The file-kind-specific verification treatment assigned to every entry in a Coverage Manifest.
_Avoid_: Ignored file, blanket line review

**Spec Gate**:
The discovery and validity result for the reviewed change's Requirement Source.
_Avoid_: Mandatory spec, ask-for-spec step

**Requirement Source**:
An issue, PRD, specification, or explicitly implementation-bound ADR that states what the reviewed change is expected to deliver.
_Avoid_: Any nearby document, architecture context

**Architectural Constraint**:
An ADR or equivalent documented decision that limits acceptable implementation choices without necessarily defining the requested feature.
_Avoid_: Spec requirement, acceptance criterion

**Review Precedence**:
The authority order used to resolve conflicts among invariants, valid requirements, architectural constraints, repository standards, and general heuristics.
_Avoid_: Repo always wins, checklist always wins

**Review Axis**:
An independent conclusion dimension whose findings are evaluated without being reranked against findings from another dimension.
_Avoid_: Module, global finding list

**PR Review Profile**:
The default delta-aware review profile that uses pull-request metadata, changed code, repository context, and existing CI evidence without repeating checks that are already proven.
_Avoid_: Full audit, shallow review

**GitHub PR Source**:
The pull-request metadata, refs, checks, and review state retrieved through the authenticated GitHub CLI for a PR Review Profile.
_Avoid_: Provider adapter, generic forge source

**Check Disposition**:
The explicit outcome explaining whether a verification was executed, satisfied by current CI evidence, not applicable, not checked, or blocked.
_Avoid_: Skipped, omitted

**Current CI Evidence**:
A successful repository check whose subject commit is the same immutable commit as the Review Snapshot.
_Avoid_: Latest CI, green branch

**Local Verification Fallback**:
The repository-native, affected-scope verification executed when Current CI Evidence does not satisfy an applicable check.
_Avoid_: Full suite by default, invented command

**PR Baseline**:
The mandatory delta-aware review work performed for every pull request regardless of optional capability activation.
_Avoid_: Quick review, shallow review

**Risk Escalation**:
The evidence-triggered increase in legwork for one Review Axis without automatically deepening unrelated axes.
_Avoid_: Every PR is deep, full pipeline by default

**Review Triage**:
The cheap pre-dispatch assessment that maps scope, risk surfaces, available evidence, and repository capabilities into an explicit Review Plan.
_Avoid_: Full scan, single complexity score

**Triage Evidence**:
The compact machine-produced facts consumed by Review Triage before any reviewer agent is dispatched.
_Avoid_: Full diff prompt, agent-discovered metadata

**Triage Collector**:
The bundled Python 3 standard-library program that gathers Triage Evidence through git, GitHub CLI, and ripgrep without modifying the reviewed repository.
_Avoid_: Reviewer agent, project dependency

**Review Plan**:
The checkable declaration of active axes, capabilities, required checks and Behavior Proofs, stress profile, agent topology, and escalation gates selected by Review Triage.
_Avoid_: Free-form tool plan, implicit module choice

**Risk Map**:
The multidimensional Review Triage result covering scope, correctness, contracts, structure, runtime, requirements, evidence availability, and pull-request state.
_Avoid_: Diff size score, one global depth

**Adaptive Topology**:
The agent arrangement that begins with one Prover and one Replay agent, then adds parallel Provers split by Affected Flow only when the Review Plan requires them.
_Avoid_: One agent per axis by default, one global agent always

**Execution Budget**:
The planned reviewer-agent and context allowance assigned by Review Triage, with recorded escalation only for unresolved blockers.
_Avoid_: Unlimited fan-out, hidden token cost

**Thermo Gate**:
The Maintainability Risk Escalation triggered by explicit depth, structural growth, central-boundary changes, refactor intent, or multiple related baseline concerns.
_Avoid_: Always-on harsh review, style pass

**Provisional Finding**:
A claim from a Prover, with a Proof Recipe or traced path, that has not yet passed Replay.
_Avoid_: Bug, confirmed finding

**Verified Finding**:
A Provisional Finding whose proof Replay confirmed against the Review Snapshot.
_Avoid_: Prover finding, likely bug

**Review Result**:
The shared evidence envelope carrying one axis-specific result kind through verification and reporting.
_Avoid_: Universal bug, global severity item

**Attention Budget**:
The reporting bound that compresses low-priority results without hiding verified blockers or mandatory requirement gaps.
_Avoid_: Finding cap, first findings only

**Snapshot Refresh**:
The bounded replacement of a stale Review Snapshot followed by re-execution of every review decision invalidated by the new pull-request head.
_Avoid_: Stale disclaimer, silently updated diff

**Review Completion**:
The terminal execution state determined by snapshot currentness, coverage, required evidence, and gate resolution independently of whether findings exist.
_Avoid_: Approval, clean result

**Approval Gate**:
The policy that permits an approval recommendation only after review execution is complete and no blocking result or critical verification gap remains.
_Avoid_: Review Completion, automatic approval

**Review Verdict**:
The final recommendation derived from Review Completion, the Approval Gate, and verified blocking or non-blocking results.
_Avoid_: Completion state, GitHub review event

**Publication Gate**:
The explicit user authorization required before Trident creates a GitHub review event or comment.
_Avoid_: Review Plan, read-only execution

**Finding Placement**:
The output location selected from whether a result has a precise, useful, GitHub-commentable changed line or instead spans files, architecture, requirements, coverage, or review state.
_Avoid_: Forced inline comment, arbitrary line attachment

**Evidence Packet**:
The complete internal support for a blocking result: claim, trigger scenario, concrete impact, code evidence, confidence, minimal correction direction, and correction verification.
_Avoid_: Published essay, hidden unsupported conclusion

**Finding Render**:
The concise developer-facing projection of a Verified Finding, preserving actionability while omitting redundant investigation detail.
_Avoid_: Evidence Packet dump, vague summary

**Developer Review**:
The compact, publication-ready GitHub review containing the verdict, blocking results, check summary, and collapsed non-blocking details.
_Avoid_: Remediation dossier, full investigation transcript

**Remediation Report**:
The detailed handoff for the person or agent resolving findings, retaining each Evidence Packet, relevant context, dependencies between findings, correction direction, and verification guidance.
_Avoid_: Public review body, terse finding list

**Remediation Markdown**:
The single structured representation of a Remediation Report, organized by stable finding IDs and readable by both humans and coding agents.
_Avoid_: Parallel JSON copy, duplicated serialization

**Artifact Persistence Gate**:
The explicit user request and destination required before Trident writes a review or remediation artifact to disk.
_Avoid_: Automatic repository file, implicit report storage

**Remediation Handoff Gate**:
The completeness check that ensures another coding agent can resolve a finding without repeating the original review investigation.
_Avoid_: Implementation plan for the whole PR, speculative rewrite

**Triage Rule**:
An explicit signal-to-capability mapping that establishes the minimum required Risk Questions, Behavior Proofs, or checks for a Review Plan.
_Avoid_: Model intuition only, optional mandatory proof

**Coverage Gap**:
An explicitly unverified area that limits confidence without itself being a finding.
_Avoid_: Suspicious finding, possible bug

**Removal Candidate**:
Code or structure proposed for deletion that still requires reachability and impact evidence before removal is considered safe.
_Avoid_: Dead code, safe deletion

**Simplification Candidate**:
A maintainability proposal that could remove concepts, branches, wrappers, or layers while preserving intended behavior.
_Avoid_: Bug, mandatory refactor

**Removal Gate**:
The on-demand reachability and impact validation that determines whether a concrete Removal Candidate is safe, deferred, unsupported, or not removable.
_Avoid_: Dead-code scan, automatic deletion

## Relationships

- A **Review Snapshot** has exactly one **Coverage Manifest**
- Every file in a **Coverage Manifest** has exactly one **Coverage Class**: source, generated, lockfile, snapshot, vendored, binary, deleted, or renamed
- A **Coverage Class** may replace line-by-line review with source-generation, provenance, behavioral, metadata, base-snapshot, or rename verification without removing the file from coverage
- A **PR Review Profile** reviews exactly one pull-request **Review Snapshot**
- A full **PR Review Profile** is GitHub-only and uses exactly one **GitHub PR Source**
- When GitHub CLI access is unavailable, Trident may review resolvable local refs but does not claim GitHub PR metadata coverage
- Every **PR Review Profile** executes the **PR Baseline**
- Every **PR Baseline** begins with **Review Triage** and produces exactly one **Review Plan** before reviewer agents are dispatched
- A bundled deterministic collector produces **Triage Evidence** without dispatching a reviewer agent
- The **Triage Collector** owns that deterministic collection and writes no artifact into the reviewed repository
- **Triage Evidence** contains snapshot, manifest, repository-capability, CI, documentation, and objective risk-signal facts without embedding the full diff
- **Review Triage** produces a **Risk Map**, never a single size-derived complexity score
- The **Review Plan** assigns depth independently per Review Axis and declares its agent and context budget
- The **Review Plan** is displayed as a concise execution notice and is not an approval gate
- After displaying the **Review Plan**, Trident continues automatically for baseline, escalated, and deep reviews because review execution is read-only
- Trident pauses after triage only when the Review Snapshot cannot be resolved, indispensable GitHub authority is unavailable without a local fallback, or a non-blocker would require exceeding the declared Execution Budget
- Every **Review Plan** applies explicit **Triage Rules** before model-selected escalation
- A **Triage Rule** establishes a minimum capability that the model may strengthen but may not remove
- Any model-selected capability beyond the Triage Rules is justified concisely in the Review Plan
- Authentication, authorization, secrets, and trust-boundary signals require the `security-trust` capability
- Schema, migration, persistence, transaction, concurrency, and cache signals require the `data-integrity` capability
- Public API, event, queue, integration, and cross-module contract signals require the `contract-integration` capability
- Visual component, frontend route, UI state, and browser-runtime signals require the `ui-runtime` capability
- New abstractions, layers, dispatchers, state machines, giant files, and branch-mode growth require thermo-depth Maintainability review
- Deletion, deprecation, and concrete deletion-oriented Simplification Candidates require the `removal-dead-code` capability through the Removal Gate
- A valid Requirement Source requires the `spec-alignment` capability
- A behavioral change without corresponding test evidence requires focused test verification and may produce a Coverage Gap
- **Risk Escalation** applies independently to Correctness, Maintainability, or Spec Alignment
- **Adaptive Topology** uses one Prover and one Replay agent at baseline, adding parallel Provers per Affected Flow, a Context Mapper, and base-differential replay as the Review Plan escalates
- **Execution Budget** allows two agents for baseline, four for escalated, and six for deep; tokens are spent on running proofs, not on additional reviewers
- An **Execution Budget** may be exceeded only to settle a concrete P0/P1 bug, Maintainability blocker, or contradictory required evidence, and the Review Plan records that escalation
- A changed pull-request head triggers **Snapshot Refresh** before any current verdict is reported
- **Snapshot Refresh** may occur at most twice; further head movement ends the run as `review_superseded`
- **Current CI Evidence** may satisfy an applicable verification without local repetition
- The absence of **Current CI Evidence** never blocks review discovery or independent source verification
- Missing **Current CI Evidence** activates the **Local Verification Fallback**
- The **Local Verification Fallback** prefers focused tests and affected-package checks over repository-wide execution
- Repository-wide verification is reserved for high-risk changes or the absence of a narrower authoritative command
- Every planned verification has exactly one **Check Disposition**
- Every review refreshes the stale or touched sections of the **System Map** and writes a **Change Context Brief** before any hypothesis
- Every source change has at least one **Behavior Proof** per **Affected Flow**
- A **Prover** produces zero or more **Provisional Findings**, **Behavior Proofs**, and **Coverage Gaps**
- A suspicion that cannot be stated as a runnable or traceable prediction is dropped, not reported
- A **Provisional Finding** becomes a **Verified Finding** only when **Replay** confirms its **Proof Recipe**
- A blocking correctness result needs **Proof Level** executed or reproduced, or traced with a recorded execution blocker, and a confirming **Replay**; otherwise it becomes an **Unproven Risk**
- A Maintainability blocker cites a documented repository rule
- Disagreements are settled by a discriminating run, never by debate
- An **Unproven Risk** prevents `approve` and yields `comment`
- Every **Review Result** belongs to exactly one **Review Axis** and one result kind
- Correctness bugs use P0-P3; Maintainability concerns, Spec gaps, Removal Candidates, and Coverage Gaps use axis-specific classifications
- The **Attention Budget** may compress advisory, P3, or low-confidence results but never omits verified P0/P1 bugs, Maintainability blockers, or mandatory Spec gaps
- **Review Completion** is `complete`, `partial`, `blocked`, or `review_superseded`
- `complete` requires a current Review Snapshot, an explicit Coverage Manifest, resolved required gates, a Check Disposition for every planned verification, verified reported results, and completed temporary-worktree cleanup
- `partial` may report useful results but can never claim the reviewed change is clean
- **Review Completion** does not imply approval; only the **Approval Gate** may authorize an approval recommendation
- The **Approval Gate** requires `Review Completion: complete`, a current Review Snapshot, no P0/P1/P2 Correctness bug, no Maintainability blocker, no missing or wrong mandatory requirement, no required check with `blocked` or `not_checked` disposition, no failed Behavior Proof, and no Unproven Risk
- P3 Correctness bugs and Maintainability advisories may remain when the approval recommendation identifies them explicitly as non-blocking
- A **Review Verdict** is exactly one of `approve`, `request_changes`, `comment`, or `no_verdict`
- `approve` requires the **Approval Gate** to pass
- `request_changes` applies when a verified P0/P1/P2 Correctness bug, Maintainability blocker, or missing or wrong mandatory requirement exists
- `comment` applies when review execution is complete and only non-blocking P3 bugs, advisories, or observations remain
- `no_verdict` applies when **Review Completion** is `partial`, `blocked`, or `review_superseded`
- Trident may autonomously analyze the PR and produce a publication-ready **Review Verdict** and review body
- The **Publication Gate** is closed by default; a recommendation never publishes itself
- `gh pr review`, inline comments, issue comments, approvals, and change requests require an explicit user request to publish
- **Finding Placement** routes a result with a precise and useful changed-line anchor to an inline-ready comment
- Results about architecture, multiple files, deleted or non-commentable lines, requirements, coverage, or review state belong in the review summary
- Trident never attaches a result to an arbitrary changed line merely to make it inline-commentable
- Every P0/P1/P2 Correctness bug, Maintainability blocker, and missing or wrong mandatory requirement has a complete **Evidence Packet** before publication
- Non-blocking results may use a reduced evidence packet when their claim, impact, and remediation remain verifiable
- A **Finding Render** summarizes the problem, impact, and actionable correction compactly and includes only the evidence needed for the developer to validate it
- The review output does not expose chain-of-thought or repeat the full investigation merely because the underlying Evidence Packet is complete
- The **Developer Review** keeps its main body to the verdict, blocking results, and verification summary; P3 results, advisories, Coverage Gaps, and supporting detail may be collapsed under `<details>`
- Inline comments in the **Developer Review** remain concise and self-contained
- The **Remediation Report** is not compacted like the Developer Review and preserves the context required to reproduce, understand, prioritize, and resolve each finding
- The **Remediation Report** includes evidence and conclusions but never private chain-of-thought
- When one or more Verified Findings exist, Trident produces both a **Developer Review** and a **Remediation Report** automatically
- When no Verified Finding exists, Trident produces only the **Developer Review** and does not create an empty Remediation Report
- The **Developer Review** and **Remediation Report** reference the same stable post-verification IDs: `COR-*`, `MNT-*`, `SPEC-*`, and `REM-*`
- Every **Remediation Report** is rendered once as **Remediation Markdown** with stable headings and finding IDs
- Trident does not generate a parallel JSON representation without a concrete integration requirement
- By default, **Remediation Markdown** is returned in the response and no review artifact is written into the reviewed repository
- The **Artifact Persistence Gate** is closed by default; writing a Markdown file requires an explicit user request and destination
- A persisted artifact must remain outside the reviewed repository unless the user explicitly selects a path inside it
- Every finding in a **Remediation Report** must pass the **Remediation Handoff Gate**
- The **Remediation Handoff Gate** requires relevant file, symbol, and line anchors; current behavior and trigger; expected behavior; impact and priority; preserved constraints; bounded correction direction; discovered exact checks; and dependencies or ordering between findings
- A remediation item does not prescribe an unnecessary refactor and does not invent verification commands that repository evidence did not establish
- A **Spec Gate** may enable or skip spec-alignment review without blocking the remaining review
- The **Spec Gate** enables Spec Alignment only when a valid **Requirement Source** is available
- An ADR is an **Architectural Constraint** unless the reviewed PR or its originating work explicitly names that ADR as the implementation target
- **Review Precedence** orders evidence as correctness/security/integrity invariants, valid requirements, Architectural Constraints, repository standards, review heuristics, then general style preferences
- Repository standards may override maintainability or style heuristics but never correctness, security, integrity, or valid requirements
- Tooling is `enforced` only when proven by Current CI Evidence or Local Verification Fallback; configuration discovery alone is `configured`
- Maintainability may produce a **Simplification Candidate**
- A **Simplification Candidate** that proposes deletion becomes a **Removal Candidate**
- The **Removal Gate** activates only for a concrete **Removal Candidate** or when the reviewed change removes or deprecates code
- A **Removal Candidate** is never treated as safely removable until the **Removal Gate** passes
- Trident has three independent **Review Axes**: Correctness, Maintainability, and Spec Alignment
- Correctness always runs; Maintainability selects a baseline or thermo-depth profile; Spec Alignment runs only when the **Spec Gate** enables it
- The **Thermo Gate** passes when the user requests structural depth, the change introduces a structural mechanism, a file crosses 1000 lines, branching modes accumulate, a central/shared boundary changes, the change is primarily a refactor, or multiple related maintainability concerns appear
- Explicit `quick` and `deep` requests override review intensity; pull-request mode alone does not imply `deep`

## Example dialogue

> **Reviewer:** "The Prover thinks a redelivered webhook charges twice. Is that a bug?"
> **Trident:** "Not yet. It becomes a finding when its Proof Recipe fails at head with the charged-twice signature and Replay confirms it; if no environment can run it, it is an Unproven Risk."

## Flagged ambiguities

- No unresolved product ambiguity remains from the grilling session. The exact
  deterministic mapping from Risk Map signals to Risk Questions, Behavior Proofs, and checks is
  executable in `references/triage-rules.md` and `scripts/collect_triage.py`.
