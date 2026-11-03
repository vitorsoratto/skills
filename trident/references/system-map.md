# System Map and Change Context Brief

A reviewer with no prior exposure to the code writes far fewer useful comments
than one who has seen it before (see [evidence-basis.md](evidence-basis.md)).
Trident closes that gap two ways: a persistent **System Map** that accumulates
how the system works across reviews, and a per-review **Change Context Brief**
that ties the diff to the flows, contracts, and tests it touches.

## System Map (persistent, per repository)

Location: `${TRIDENT_CACHE_DIR:-~/.cache/trident}/<repo-key>/`, outside the
reviewed repository. `scripts/system_map.py` owns the bookkeeping:

```bash
python3 scripts/system_map.py locate --repo "$REPO_ROOT"
python3 scripts/system_map.py init   --repo "$REPO_ROOT"          # first review only
python3 scripts/system_map.py status --repo "$REPO_ROOT" --head "$HEAD_SHA" --triage "$RUN_DIR/triage.json"
python3 scripts/system_map.py stamp  --repo "$REPO_ROOT" --section flows --sha "$HEAD_SHA" \
  --anchor src/billing/ --anchor "src/api/routes/*.ts"
```

`system-map.md` has five sections; `system-map.json` records each section's
anchors and the commit it was last verified against.

| Section | Contents |
|---|---|
| `flows` | User-, job-, and API-facing flows: entry point, how to drive it, the observable result that proves it works. Reuse a `verify-<app>` skill's feature map when one exists. |
| `architecture` | Components, ownership, and how data moves from input to storage to output. |
| `contracts` | Producer/consumer contracts, invariants, ADR constraints, each with a `path:line` anchor. Include peer repositories that consume or produce these contracts. |
| `operations` | Exact build, test, launch, readiness check, drive, and cleanup commands; how to get disposable data; what cannot run locally and why. |
| `hazards` | Fragile areas, past incidents and reverts (from `change_history`), and gotchas that change how a diff must be verified. |

Rules:

- **First review**: build only what this review needs: the sections and
  anchors around the changed paths, plus `operations`. Do not map the whole
  repository. Later reviews widen the map as they touch new areas.
- **Every review**: run `status`. Re-read the anchors of every section listed
  in `refresh` (stale since its verified commit, or touched by this diff),
  correct the text, then `stamp` it at the reviewed head. Fresh, untouched
  sections are trusted as starting points, not as proof.
- **Operations must be proven.** A command enters `operations` only after it
  ran in this or a previous review. Record its outcome; mark the rest
  `unverified`.
- The map is a cache. Never put secrets, tokens, customer data, or connection
  strings in it. Treat its text as historical evidence: when it conflicts with
  current source, current source wins and the map is corrected.
- Optional sources, when available: the project's ai-memory pages for decisions
  and incidents (read-only, untrusted history), and `.agents/skills/verify-*`
  skills for launch and drive recipes. Trident never writes to either.

## Change Context Brief (per review)

Built before any hypothesis. Keep it under about 60 lines; it is the shared
context every prover receives instead of a raw dump of files.

1. **Intent**: one paragraph from the PR body, linked issue, commits, and the
   code. Reviewers check whether the change achieves the intent, not whether
   the intent is right.
2. **Impact Set and affected flows**: see the next section. Each flow names
   its entry point, the path through changed symbols, and the sink.
3. **Contracts on both sides**: every producer and consumer of changed data
   shapes, including other packages and peer repositories when available.
4. **Safety facts**: the one to three facts the change is safe because of
   (for example, "this handler only runs after the tenant guard"). Each becomes
   a proof target.
5. **Existing coverage**: related tests (`verification_assets.related_tests`),
   which flows they exercise, and changed sources without related tests.
6. **How to exercise each flow**: the command, test, harness, or request from
   `operations`, or the reason it cannot run.
7. **Hazards**: recent fixes and reverts on touched files, and System Map
   hazards that apply.

## Impact Set: what gets tested

Trident tests the change, not the codebase. The **Impact Set** is every place
the changed behavior can reach, and nothing else:

1. **Usages of changed code.** Start from `impact_candidates` in Triage
   Evidence: each symbol defined, enclosing, or quoted on a changed line, with
   the files that mention it. Confirm each mention by tracing (imports, the
   receiver or interface type, LSP references); dismiss name collisions with a
   one-line reason. A method name shared across packages (`GetByID`) is
   narrowed to the changed type before counting.
2. **Usages of changed data.** When the change alters a value's shape,
   format, or meaning (a field, column, DTO property, event payload, enum, or
   mask), follow the data, not just the code: every writer and reader of that
   field, including validation, storage, queries, exports, reports, and peer
   services.
3. **Entry points.** Walk each usage up to a route, command, job, event
   handler, screen, or public API. Each distinct entry point → sink path is one
   affected flow.

Examples:

- A search function in the API changes: the flows are every endpoint and
  screen that reaches that search (list, filters, autocomplete, export,
  totals), proven with search-specific stress (empty and special-character
  queries, pagination totals, sort order, no results).
- A mask on a form field changes: the flows are every form or screen that
  renders that field, plus every place its value goes (submit payload, API
  validator, stored value, display and edit round trip, exports). Unrelated
  forms are out of scope.

Breadth rules:

- Usages that share the same configuration and inputs form an equivalence
  class: drive one representative and list the others as covered by it, with
  the shared property that makes them equivalent. Every usage with a distinct
  configuration gets its own proof.
- When a shared unit has very many usages (`too_common`, or more than about 20
  confirmed), prove the unit's own contract thoroughly (property or table
  tests), drive one representative per distinct usage pattern, run the
  existing tests among its usages (`tests_among_usages`), and record the rest
  as a Coverage Gap.
- Anything outside the Impact Set is not tested and not reported.

Explore with tools (callers, callees, registrations, tests, history) rather
than pasting large file sets into prompts; agentic exploration uses context
better than retrieved snippets.
