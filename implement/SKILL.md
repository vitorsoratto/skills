---
name: implement
description: Implement what this conversation settled (a grill spec or plain chat), as an orchestrator that routes work to the right model per role. Say "economia" to spend fewer tokens.
argument-hint: "[economia] [trident] [extra instructions]"
disable-model-invocation: true
---

# Implement

You are the **orchestrator**. You hold the conversation's context: you decide, brief, integrate and verify. Workers do the hands-on work whenever that is faster or better than doing it yourself.

Work autonomously. When something is unclear, pick the option most consistent with the brief, log it as an assumption, and keep going. Explicit instructions in the arguments or the user's last message override every default below.

## 1. Pick the mode

- **full** (default): best result in the least wall-clock time. Tokens are not the constraint.
- **lean**: the user signals budget ("economia", "barato", "gastei muito", "sem subagentes"). Spend as few Claude tokens as the result allows. Lean changes are marked _lean_ below.

## 2. Write the brief

The **brief** is the single source of truth every worker and any new thread reads. Gather:

- specs and docs the conversation produced or named: `SPEC.md`, `docs/adr/`, `GLOSSARY.md`, ai-memory decision pages;
- what the chat settled, including anything decided after the spec was written.

The brief holds:

1. Goal, in one paragraph.
2. Sources, with absolute paths and which one wins a conflict.
3. Decisions settled, each with its rejected alternative, so no one reopens it.
4. Scope and out of scope.
5. Guardrails: what must not be touched or done.
6. Done: the commands whose output proves it works (tests, build, typecheck, running the app). Adjectives are not criteria.
7. Assumptions and open items.

When a spec already covers all of this, the brief points to it and adds only the delta. Save the brief as `implement-brief.md` in your scratchpad directory (or a temp directory) and keep its absolute path.

Done when every decision from the chat appears in the brief or in a source it points to.

## 3. Route the work

| Situation | Route |
|---|---|
| Small: one area, about 3 files or fewer, a handful of tool calls | Do it yourself here. No workers. |
| Medium or large, and this conversation is light | Orchestrate here (steps 4 and 5). |
| This conversation is **heavy**: it was compacted, or long file dumps and many turns put it past roughly 60% of your window | **Hand off** to a new thread. |

**Hand off:** in T3 Code, call `t3_thread_launch` in the same project with the prompt `/implement <mode> — the brief at <absolute path> is your full context; this conversation is not available to you.` Reply with the thread link and stop. Outside T3 Code, give the user that line to paste into a new chat.

_Lean:_ a heavy conversation re-reads its whole context on every orchestration turn, so handing off is usually the cheaper route too.

## 4. Plan in blocks

Split the work into **blocks**. Each block names the files it owns, what it depends on, its worker (table below), and its validation command.

- If blocks share an interface (API, types, schema), define that contract first, in one place. It unblocks parallel work.
- Start every block with no unmet dependency at once: several `Agent` calls in one message run in parallel.
- Two workers never edit the same file at the same time. When that is unavoidable, give one `isolation: "worktree"`.

## 5. Dispatch workers

| Role | Worker | Examples |
|---|---|---|
| Mechanical, well defined | Opus 5.5 **low** | scaffolding, renames, repetitive edits, config, fixtures, running builds and summarising errors, docs |
| Needs judgment | Opus 5.5 **medium** | a module, an integration, debugging, a careful refactor, tests that matter |
| A second model's eye, or volume | DeepSeek V4.1 Flash **max** | adversarial review of a diff, checking whether a reported bug is real, hunting edge cases, generating test cases |
| Architecture, contracts, integration, final say | you | |

How to call:

- Opus: native `Agent` with `model: "opus"` and `effort` from the table.
- DeepSeek: `delegate_task` (another provider). Call `orchestrator_capabilities` once first, then target provider `opencode`, model `opencode/deepseek-v4.1-flash`, option `variant: max`. If it is unavailable, try `opencode-go/deepseek-v4.1-flash`, then fall back to Opus medium and note it in the report.

Every worker starts blind, so its prompt carries:

- the goal and why, plus the brief's path and the section it implements;
- the files it owns and what it must not touch;
- the guardrails;
- its done criterion and validation command;
- the reply format: files changed, validation evidence, assumptions.

Workers decide on their own without asking, start no workers of their own, and leave memory writes to you.

_Lean:_ prefer doing a block yourself over briefing a worker when the brief would be longer than the work. Keep the DeepSeek reviews, which cost no Claude tokens.

## 6. Verify and close

1. **Per block:** run its validation and read the diff yourself before integrating. A worker's report is a claim, not evidence.
2. **Final:** run the full done criteria from the brief. Send the whole diff to DeepSeek for adversarial review. Confirm each finding (reproduce it, or have a second worker check it) before fixing. Repeat until clean, at most 3 rounds (_lean:_ 1).
   When the user asks for Trident, it replaces this review: invoke the `trident-converge` skill on the diff instead, and keep step 1 as is.
3. **Record:** decisions made during implementation go where the brief's decisions live (spec, ADR, or ai-memory page).

Finish everything else, and leave for the user only what is irreversible and outside the brief: deleting data you did not create, pushing to main or production, spending money, messaging people.

Report, short:

1. The result in one sentence.
2. What changed (files, services).
3. Validation evidence: commands and results.
4. Assumptions made.
5. **Action:** what is left for the user, in order.
