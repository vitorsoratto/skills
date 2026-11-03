# Evidence Basis

Why Trident v3 proves by execution and builds system context instead of
running adversarial reviewer, verifier, and judge lanes. Researched
2026-11-03. Vendor figures are self-reported and marked as such.

## What review finds

| Finding | Source | Design consequence |
|---|---|---|
| 14% of 570 review comments were defects; understanding the change is the main challenge, and not knowing the files is a major cause. | Bacchelli & Bird, ICSE 2013 | Few real defects per review. Build understanding first (Change Context Brief). |
| About 15% of comments flag a possible defect; at least 50% concern maintainability. | Czerwonka, Greiler & Tilford, Microsoft 2015, "Code Reviews Do Not Find Bugs" | A bug-focused review must filter hard (Signal policy). |
| Reviewers new to the code have about 33% useful comments; by their third review of the same code, about 67%. Usefulness drops for reviews of 20+ files. | Czerwonka et al. 2015, summarizing Bosu et al., MSR 2015 | Persist familiarity across reviews (System Map). Split provers by flow for large diffs. |
| Google's median change is 24 lines with one reviewer; review is mostly education and norms. | Sadowski et al., ICSE-SEIP 2018 | One informed reviewer beats many uninformed ones. |
| Low review coverage and participation link to more post-release defects; context-aware metrics predicted better than generic ones. | McIntosh et al., MSR 2014; Shimagaki et al., ICSE-SEIP 2016 | Engage deeply with the risky files rather than broadly with all. |

## AI review signal and noise

| Finding | Source | Design consequence |
|---|---|---|
| AI suggestions adopted 16.6% vs 56.5% for humans across 278,790 conversations. | Zhong et al., 2026, arXiv 2603.15911 | Default AI comments are mostly noise; require proof. |
| Best GitHub AI review action: 19.2% of comments valid and addressed; concise comments with code snippets were acted on more. | Sun et al., 2025, arXiv 2508.18771 | Short findings, exact anchors, proof command attached. |
| Industrial LLM reviewer: 73.8% comments resolved, but PR close time rose from 5h52m to 8h20m. | Cihan et al., ICSE-SEIP 2025, arXiv 2412.18531 | Noise has a latency cost; fewer, proven findings. |
| Google ML-suggested edits filter by confidence, trading quantity for quality. | Google Research blog, 2023 | Report nothing below the proof bar. |
| Parallel finders, then a verification filter, then ranking; under 1% of findings marked incorrect (self-reported). | Anthropic, "Code Review", March 2026 | Keep parallel discovery plus a filter, but make the filter execution. |
| Best tool about 19% F1 on 1,000 PRs; aggregating several independent reviews raised F1 by up to 43.67%. | Zeng et al., 2025, SWR-Bench, arXiv 2509.01494 | Independent provers per flow, then dedupe. No debate rounds. |

## Reading-only verification and debate

| Finding | Source | Design consequence |
|---|---|---|
| Self-correction without external feedback lowers accuracy (GPT-4 GSM8K 95.5 → 89.0). | Huang et al., ICLR 2024, arXiv 2310.01798 | A verifier that only rereads can delete true findings. |
| Majority voting explains most multi-agent debate gains; debate alone does not raise expected correctness. | Choi et al., NeurIPS 2025, arXiv 2508.17536; Smit et al., ICML 2024 | Arbiter and counter-argument stages removed. |
| Tool-interactive critique consistently improves results; self-repair is bounded by the model's own feedback quality. | Gou et al., CRITIC, ICLR 2024; Olausson et al., ICLR 2024 | Verification must use tools: run the code. |
| Running generated tests in a loop raised GPT-4 from 19% to 44% pass@5 on CodeContests. | Ridnik et al., AlphaCodium, 2024 | Execution is the highest-return verification. |
| LLM critics catch more bugs than humans but hallucinate nitpicks; longer critiques hallucinate more. | McAleese et al., CriticGPT, 2024 | Cap output and suppress nitpicks. |

## Empirical and formal verification

| Finding | Source | Design consequence |
|---|---|---|
| Generated tests filtered through build → pass → coverage gates: 73% of recommendations accepted. | Alshahwan et al., Meta TestGen-LLM, FSE 2024 | Gate proofs mechanically (replay script). |
| Mutation-guided test generation: 73% of tests accepted. | Foster et al., Meta ACH, FSE 2025 | "Write a test that kills this fault" is a strong probe. |
| Productive mutants rose from 15% to 89% after filtering unproductive ones. | Petrović et al., Google, 2021 | Filter probes for relevance before spending on them. |
| Each property-based test killed about 50x the mutants of an average unit test. | Ravi & Coblenz, OOPSLA 2025 | Prefer property tests for `boundary` stress. |
| A 35-step DynamoDB bug passed design reviews, code reviews, and testing; TLA+ found it. | Newcombe et al., CACM 2015 | Use model checking for interleavings when the repo has a spec. |

## Practitioner designs this follows

- pstack `interrogate` (cursor/plugins, updated 2026-10): a finding survives
  only if a run against the real code proves it; leave out anything not run;
  "no findings is a valid result."
- pstack `blast-radius`: find the one fact the change is safe because of and
  prove it by running code; the proof ladder in this skill derives from it.
- pstack `create-verification-skill`: a project-local recipe to launch, check,
  drive, and capture evidence, with a feature map; Trident reuses such skills
  in the System Map `flows` and `operations` sections.
- entireio `review`: build an intent map before reading the diff; one finding
  per root cause; no style comments unless they break a project convention.

## Not verified

Not relied on: Mäntylä & Lassenius's "75% evolvability" figure (secondary
sources disagree), SmartBear/Cisco 200–400 LOC guidance (vendor), and vendor
precision claims for Bugbot, Greptile, Graphite, and the Martian leaderboard.
No study was found that isolates call-graph context for AI review; AACR-Bench
(Zhang et al., 2026, arXiv 2601.19494) only shows context helps agentic
reviewers and can hurt non-agentic ones.
