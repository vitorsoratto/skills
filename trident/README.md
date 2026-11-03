# Trident

Execution-first review for GitHub pull requests and local git changes.

Trident reviews a change by running it:

1. **Context**: keeps a System Map of how the repository works (flows, contracts, how to run things, hazards) outside the repo, and refreshes only what the change touches.
2. **Prove**: drives each affected flow end to end, runs the proofs its risk requires (authorization matrix, retry/idempotency, concurrency, contract round-trip, UI states), and applies a stress profile scaled to risk.
3. **Replay**: re-runs every claimed bug in fresh worktrees at head and base. Only confirmed runs can block a PR; everything else is reported as an Unproven risk.

Style, naming, "add tests", and hypothetical concerns are not reported. See `references/evidence-basis.md` for the research behind this design.

## Install

```bash
npx skills add vitorsoratto/skills --skill trident
```

## Use

```text
/trident https://github.com/org/repo/pull/42
/trident quick staged
/trident deep main..feature-auth
/trident src/api/
```

PR review never modifies your checkout. Trident runs code only in its own disposable worktrees, and only for same-repository PRs or local changes unless you allow a fork. It returns a compact Developer Review and, when findings exist, a Remediation Report whose Proof Recipes Trident Fix reruns. Publishing to GitHub requires an explicit request.

The System Map cache lives in `${TRIDENT_CACHE_DIR:-~/.cache/trident}`.
