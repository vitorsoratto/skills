# Skills

Custom agent skills for Claude Code.

## Available Skills

### trident

Three-pronged code review pipeline that combines broad scanning, independent verification, and evidence-based judgment.

```bash
npx skills add vitorsoratto/skills --skill trident
```

### mongodb-expert

MongoDB expert advisor with fact-checked, version-aware guidance. Enforces a research pipeline against official documentation before any recommendation. Covers ReplicaSets, WiredTiger, oplog, TimeSeries, data modeling, performance, aggregation, and production hardening. Focused on MongoDB 8.x+.

```bash
npx skills add vitorsoratto/skills --skill mongodb-expert
```

## Install

List all available skills:

```bash
npx skills add vitorsoratto/skills --list
```
