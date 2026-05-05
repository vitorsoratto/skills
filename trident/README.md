# Trident

Tool-aware, modular code review pipeline that combines multi-lens scanning, adversarial edge-case review, independent verification, and evidence-based final judgment.

## Installation

Install with the Skills CLI:

```bash
npx skills add vitorsoratto/skills --skill trident
```

Or copy this directory to your skills folder manually:

```bash
cp -r trident/ ~/.agents/skills/trident/
```

## Features

### Two review depths
- **Quick** — Scanner plus cheap active modules, then Verifier for small local diffs and fast triage
- **Deep** — Scanner plus deep active modules, then Verifier and Arbiter for PRs, ranges, directories, and risky changes

### Multi-Lens Scanning
- **SOLID Principles** — SRP, OCP, LSP, ISP, DIP violations + code smells
- **Security** — XSS, injection, SSRF, race conditions, auth gaps, secrets, crypto
- **Code Quality** — Error handling, performance (N+1, caching), boundary conditions
- **Data Integrity** — Transactions, idempotency, concurrent modifications
- **Dead Code Detection** — Removal candidates with safe deletion plans

### Evidence-focused pipeline
- **Forced Counterarguments** — Scanner must state strongest reason each finding might be wrong
- **Tool Routing** — Chooses git, rg, gh, tests, browser tools, docs, and CI evidence based on the review target
- **Specialist Modules** — Adds quick/deep lanes for edge functions, security, data integrity, contracts, UI runtime, and dead-code review
- **Edge Functions** — Breaks changed functions with extraordinary but realistic inputs while still checking the essential path
- **Independent Verification** — Verifier re-reads code, confirms/rejects each finding
- **Evidence-Based Judgment** — Arbiter renders final verdicts in deep reviews
- **Unified YAML Contract** — Core stages and modules preserve the same finding schema
- **Bounded Recall** — Quick mode caps findings at 6, deep mode at 15

### Review-First Workflow
- Structured output with P0-P3 severity levels
- Executable commands and concrete batching rules for large diffs
- Worktree cleanup runs even on interruption or failure
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
- `/trident quick` — fast local triage
- `/trident deep staged` — full review of staged changes
- `/trident staged` — review staged changes
- `/trident https://github.com/org/repo/pull/42` — review PR #42
- `/trident main..feature-auth` — review branch diff
- `/trident src/api/` — audit entire directory

## Pipeline

1. **Scanner** — Multi-lens scan with forced counterarguments
2. **Specialist modules** — Optional quick/deep lanes such as edge-functions and data-integrity
3. **Verifier** — Independent verification that contests Scanner and module findings
4. **Arbiter** — Final judgment for deep reviews and disputed high-risk findings

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
│   ├── edge-functions-prompt.md  # Specialist: adversarial function edge cases
│   ├── verifier-prompt.md        # Agent 2: independent verification
│   └── arbiter-prompt.md         # Agent 3: final judgment
└── references/
    ├── solid-checklist.md        # SOLID smell prompts
    ├── security-checklist.md     # Security & reliability
    ├── code-quality-checklist.md # Error, perf, boundaries
    ├── edge-functions-checklist.md # Extraordinary function cases
    ├── module-playbook.md        # Module activation and quick/deep rules
    ├── tool-playbook.md          # Tool selection guidance
    └── removal-plan.md           # Deletion planning template
```

## License

MIT
