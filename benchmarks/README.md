# Enterprise Insight Benchmark

## v1 repeatable runner

Run from the repository root (PowerShell: use `.venv/Scripts/python`):

```sh
python -m benchmarks.run --variant baseline --split development --output outputs/baseline-dev-dry
python -m benchmarks.run --variant source_aware --split development --output outputs/source-aware-dev-dry
# Adding --live executes provider/search calls. Use a NEW output directory each time.
# Reserve --split holdout for the final comparison.
python -m benchmarks.score --run-dir outputs/baseline-dev --annotations annotations.json --output outputs/baseline-dev-scored
```

The JSON configurations compare the **current implementation with weight 0 vs 0.2**.
This is a same-version ablation, distinct from the historical upstream baseline below.
Weight 0.2 is a candidate, not an optimized value. Configuration overrides that change
frozen settings are rejected. Dry runs validate inputs and write manifests but execute
no research and report no measured quality, latency, or costs.

Each live run writes a timestamp, commit SHA, dataset hash, frozen configuration,
per-case input/report/context/sources/evidence/metrics, and aggregate JSON results.
Failures remain in the failure-rate denominator. Exception classes are recorded without
potentially sensitive provider messages. Existing directories are never overwritten.
Cost is the existing provider's estimate, not an invoice; unsupported model pricing may
be incomplete. Search-call counts are null until instrumented, never inferred from URLs.

The four quality metrics require reviewed counts following `docs/baseline_protocol.md`.
An annotation is a JSON array of `QualityAnnotation` objects (schema in
`benchmarks/metrics.py`), including run ID, exact report SHA-256, reviewer and method.
Each factual claim must be classified as supported or unsupported. Zero citation/claim
denominators yield null. Missing annotations yield null, and scoring writes a separate
artifact rather than modifying raw runs. Required facts should be defined from each
case's required dimensions **before** reviewing variants; dimensions are not automatically
treated as verified facts. Citation presence alone never establishes support.

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
