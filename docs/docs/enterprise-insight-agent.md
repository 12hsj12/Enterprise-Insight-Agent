# Enterprise Insight Agent

Enterprise Insight Agent is a local reference implementation for competitive intelligence and related enterprise research. It brings source-aware research, structured evidence, answer-critical claim review, citation grounding, and inspectable report records into one product flow.

## Start here

- [Project README and quick start](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/README.md)
- [Local deployment guide](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/docs/deployment.md)
- [Request walkthrough and synthetic demo](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/docs/demo.md)

## Architecture and implementation

- [Architecture specification](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/docs/v2/V2_ARCHITECTURE_SPEC.md)
- [Information-flow note](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/docs/v2/INFORMATION_FLOW_SIMPLIFICATION.md)
- [Core evidence modules](https://github.com/12hsj12/Enterprise-Insight-Agent/tree/main/gpt_researcher/evidence)
- [Enterprise workflow modules](https://github.com/12hsj12/Enterprise-Insight-Agent/tree/main/gpt_researcher/enterprise)
- [Enterprise API and SQLite store](https://github.com/12hsj12/Enterprise-Insight-Agent/tree/main/backend/server)

## Tests and evaluation

- [Offline test runner](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/scripts/run_offline_tests.py)
- [Frozen benchmark specification](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/docs/v2/V2_BENCHMARK_SPEC.md)
- [One-pass holdout review](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/docs/v2/V2_HOLDOUT_ONE_PASS_EVALUATION.md)
- [Historical ablation results, including holdout regressions](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/benchmarks/results/v1/final_quality_comparison.md)

The holdout completed all 12 case executions, while the human review outcome was **MIXED**. Runtime completion is reported separately from report quality. Historical ablation results remain in the evaluation record and are not a score for the current product.

## Scope and provenance

This repository retains GPT Researcher's research and writing foundations. The separate **GPT Researcher reference** sections in the sidebar document upstream capabilities and historical setup material; use the Enterprise Insight Agent links above for this repository's current product flow. License details are in the [repository LICENSE](https://github.com/12hsj12/Enterprise-Insight-Agent/blob/main/LICENSE).
