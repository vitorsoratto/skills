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

## Install

List all available skills:

```bash
npx skills add vitorsoratto/skills --list
```
