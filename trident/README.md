# Trident

Three-pronged code review pipeline that combines multi-lens scanning with independent 3-agent verification to produce high-confidence findings with minimal false positives.

## Installation

Copy this directory to your skills folder, or install manually:

```bash
cp -r trident/ ~/.agents/skills/trident/
```

## Features

### Multi-Lens Scanning (from code-review-expert)
- **SOLID Principles** — SRP, OCP, LSP, ISP, DIP violations + code smells
- **Security** — XSS, injection, SSRF, race conditions, auth gaps, secrets, crypto
- **Code Quality** — Error handling, performance (N+1, caching), boundary conditions
- **Data Integrity** — Transactions, idempotency, concurrent modifications
- **Dead Code Detection** — Removal candidates with safe deletion plans

### Independent Verification Pipeline (from repo-review)
- **Forced Counterarguments** — Scanner must state strongest reason each finding might be wrong
- **Independent Verification** — Verifier re-reads code, confirms/rejects each finding
- **Evidence-Based Judgment** — Arbiter renders final verdicts with tiered verification
- **Permission to Abstain** — INSUFFICIENT_EVIDENCE and NEEDS_HUMAN_CHECK for genuine ambiguity
- **Bounded Recall** — Hard cap on findings to prevent noise (15 max)

### Review-First Workflow
- Structured output with P0-P3 severity levels
- Never implements changes without user confirmation
- Next-steps menu for user decision

## Usage

After installation, invoke:

```
/trident
```

### Review Modes

Trident automatically detects what to review based on your input:

| Mode | How to Trigger | What It Reviews |
|------|---------------|-----------------|
| **Unstaged** | Default (no target) | `git diff` — working tree changes |
| **Staged** | Say "staged" | `git diff --cached` — staged for commit |
| **All local** | Say "all local" or "everything" | `git diff HEAD` — staged + unstaged |
| **Pull Request** | Provide PR URL, number, or say "review PR" | `gh pr diff` — remote PR diff |
| **Commit range** | Provide range (`abc..def`) or branch name | `git diff A..B` — two refs |
| **Directory** | Provide a path (e.g., `src/api/`) | Full directory audit |

Examples:
- `/trident` — review unstaged changes
- `/trident staged` — review staged changes
- `/trident https://github.com/org/repo/pull/42` — review PR #42
- `/trident main..feature-auth` — review branch diff
- `/trident src/api/` — audit entire directory

## Pipeline

1. **Scanner** — Multi-lens scan with forced counterarguments (SOLID, security, quality, dead code)
2. **Verifier** — Independent verification with falsification attempts
3. **Arbiter** — Evidence-based final judgment with tiered verification

## Severity Levels

| Level | Name | Action |
|-------|------|--------|
| P0 | Critical | Must block merge |
| P1 | High | Should fix before merge |
| P2 | Medium | Fix or create follow-up |
| P3 | Low | Optional improvement |

## Structure

```
trident/
├── SKILL.md                      # Main skill definition
├── agents/
│   └── agent.yaml                # Agent interface config
├── prompts/
│   ├── scanner-prompt.md         # Agent 1: multi-lens scan
│   ├── verifier-prompt.md        # Agent 2: independent verification
│   └── arbiter-prompt.md         # Agent 3: final judgment
└── references/
    ├── solid-checklist.md        # SOLID smell prompts
    ├── security-checklist.md     # Security & reliability
    ├── code-quality-checklist.md # Error, perf, boundaries
    └── removal-plan.md           # Deletion planning template
```

## Merged From

- **code-review-expert** — Multi-lens scanning, severity taxonomy, structured output, review-first workflow, reference checklists
- **repo-review** — 3-agent pipeline, forced counterarguments, independent verification, bounded recall, bug_id traceability, permission to abstain

## License

MIT
