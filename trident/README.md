# Trident

Risk-triaged, evidence-backed review for GitHub pull requests and local git changes.

Trident starts with deterministic scope collection, builds a multidimensional Risk Map, and activates only the review capabilities needed for the change. Correctness and baseline Maintainability always run; Thermo, Spec Alignment, contract, security, data, UI, and removal depth are gate-driven.

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

PR review is read-only by default. Trident returns a compact Developer Review and, when findings exist, a detailed Markdown Remediation Report. Publishing a GitHub approval, change request, or comment requires an explicit request.

See [SKILL.md](SKILL.md) for the workflow and `references/` for gate and output contracts.
