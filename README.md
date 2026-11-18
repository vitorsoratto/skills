# Skills

Custom agent skills for Claude Code.

## Available Skills

### trident

Execution-first code review: builds a persistent map of how the system works, proves affected flows end to end with stress cases, and reports only bugs a replayed run confirms.

```bash
npx skills add vitorsoratto/skills --skill trident
```

### mongodb-expert

MongoDB expert advisor with fact-checked, version-aware guidance. Enforces a research pipeline against official documentation before any recommendation. Covers ReplicaSets, WiredTiger, oplog, TimeSeries, data modeling, performance, aggregation, and production hardening. Focused on MongoDB 8.x+.

```bash
npx skills add vitorsoratto/skills --skill mongodb-expert
```

### criar-ticket

Entrevista objetiva para o suporte transformar uma solicitação em um ticket claro, pronto para copiar no ClickUp.

```bash
npx skills add vitorsoratto/skills --skill criar-ticket
```

### implement

Implement what the conversation settled (a grill spec or plain chat) as an orchestrator: writes a brief, splits the work into blocks, routes each block to the right model per role, and verifies before closing. Say "economia" for a lean, low-token run.

```bash
npx skills add vitorsoratto/skills --skill implement
```

## Install

List all available skills:

```bash
npx skills add vitorsoratto/skills --list
```
