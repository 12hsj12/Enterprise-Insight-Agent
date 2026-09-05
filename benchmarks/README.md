# Enterprise Insight Benchmark

This directory contains the benchmark and evaluation assets for the **Enterprise Insight Agent** project.

The benchmark is used to measure whether the engineering modifications to GPT Researcher improve evidence reliability, traceability, and enterprise research quality.

## Directory Structure

```text
benchmarks/
├── dataset/
│   └── enterprise_insight_bench_v0.json
│
├── configs/
│   └── baseline_config.yaml
│
├── baseline/
│   ├── raw_runs/
│   ├── reports/
│   └── baseline_summary.csv
│
└── README.md
```

### `dataset/`

Contains the fixed benchmark dataset.

Current dataset:

`enterprise_insight_bench_v0.json`

It contains 12 enterprise research tasks:

- 8 development cases
- 4 hold-out cases

The hold-out set must not be used for tuning.

### `configs/`

Contains frozen experiment configurations.

`baseline_config.yaml` records the environment and major parameters used by the GPT Researcher baseline.

API keys and other secrets must never be stored here.

### `baseline/raw_runs/`

Stores raw artifacts produced by individual baseline executions.

A run should use a unique ID such as:

```text
baseline_EI001_20260905_001
```

When available, each run may contain:

```text
input.json
report.md
sources.json
context.json
metrics.json
errors.json
```

Artifacts that the original baseline cannot expose should remain unavailable rather than being reconstructed manually.

### `baseline/reports/`

Stores baseline-generated research reports used for later evaluation and Before/After comparison.

### `baseline/baseline_summary.csv`

Stores run-level benchmark statistics.

Initial fields include:

```text
run_id
case_id
version
latency_s
sources
llm_calls
input_tokens
output_tokens
estimated_cost
error
```

Additional evidence-quality metrics will be added after the evaluation pipeline is implemented.

## Evaluation

The core quality metrics are:

- Evidence Coverage
- Citation Correctness
- Citation Completeness
- Unsupported Claim Rate

Engineering metrics include:

- Latency
- Source Count
- LLM Calls
- Token Usage
- Estimated API Cost
- Failure / Error Status

All benchmark values must come from actual experiment runs.

No benchmark result should be manually invented or modified to improve the final comparison.

## Evaluation Protocol

The complete experimental rules are documented in:

`docs/baseline_protocol.md`

The protocol defines controlled variables, metric definitions, raw-run requirements, hold-out rules, and Before/After comparison principles.

## Reproducibility

The intended experiment chain is:

```text
Benchmark Case
    ↓
Frozen Configuration
    ↓
Agent Execution
    ↓
Raw Run Artifacts
    ↓
Generated Report
    ↓
Evidence Evaluation
    ↓
Metrics
    ↓
Before / After Comparison
```

This benchmark will be used throughout the project to evaluate the original GPT Researcher baseline and subsequent Enterprise Insight Agent versions.