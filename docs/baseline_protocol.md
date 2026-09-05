# Enterprise Insight Agent — Baseline Evaluation Protocol

## 1. Purpose

This document defines the baseline evaluation protocol for the Enterprise Insight Agent project.

The baseline is the original GPT Researcher v3.6.1 system before the project's core engineering modifications.

All subsequent versions must be evaluated against this baseline under controlled and reproducible conditions.

The benchmark is designed to answer one central question:

> Do the proposed engineering modifications actually improve the reliability, traceability, and practical value of enterprise research results?

---

## 2. Baseline Version

- Upstream project: GPT Researcher
- Baseline version: v3.6.1
- Baseline tag: `baseline-gpt-researcher-v3.6.1`
- Benchmark cutoff date: `2026-09-05`
- Benchmark dataset: `enterprise_insight_bench_v0.json`
- Baseline configuration: `benchmarks/configs/baseline_config.yaml`

The baseline source code must not be modified to artificially improve benchmark performance.

---

## 3. Benchmark Dataset

The benchmark contains 12 enterprise research tasks.

Dataset split:

- Development set: 8 cases
- Hold-out set: 4 cases

The tasks cover:

- single-enterprise factual research
- multi-company comparison
- time-sensitive research
- multi-source synthesis
- conflicting information
- strategic decision support

The hold-out cases must not be used to tune retrieval thresholds, ranking strategies, prompts, or evidence-scoring rules.

---

## 4. Controlled Variables

For fair Before/After comparison, the following variables should remain unchanged unless the experiment explicitly studies that variable:

- benchmark query
- benchmark cutoff date
- LLM provider and model
- embedding model
- retriever
- maximum search results per query
- research iteration limit
- maximum subtopics
- target report length
- report format

The frozen values are recorded in:

`benchmarks/configs/baseline_config.yaml`

If a variable must change because it is part of the proposed engineering modification, the change must be explicitly documented.

---

## 5. Core Evaluation Metrics

### 5.1 Evidence Coverage

Measures whether important benchmark facts or conclusions are supported by valid evidence.

Evidence Coverage = supported required facts / total required facts

Higher is better.

### 5.2 Citation Correctness

Measures whether a citation actually supports the claim associated with it.

Citation Correctness = valid supporting citations / total evaluated citations

Higher is better.

### 5.3 Citation Completeness

Measures how many factual claims in the generated report have corresponding evidence.

Citation Completeness = factual claims with evidence / total factual claims

Higher is better.

### 5.4 Unsupported Claim Rate

Measures factual claims that cannot be traced to valid supporting evidence.

Unsupported Claim Rate = unsupported factual claims / total factual claims

Lower is better.

---

## 6. Engineering Metrics

Each benchmark run should additionally record:

- total latency
- number of retrieved sources
- number of LLM calls
- input tokens
- output tokens
- estimated API cost
- execution errors

If the original GPT Researcher baseline cannot expose a metric, record the value as `null`.

Do not modify the baseline solely to make unavailable observability data available.

Such missing information should instead be documented as a baseline observability limitation.

---

## 7. Raw Run Records

Each benchmark execution should use a unique run ID.

Example:

`baseline_EI001_20260905_001`

When available, the run directory should contain:

- `input.json`
- `report.md`
- `sources.json`
- `context.json`
- `metrics.json`
- `errors.json`

Unavailable baseline artifacts should be recorded as missing or `null`, rather than reconstructed after execution.

---

## 8. Evaluation Rules

Benchmark results must come from actual executions.

Do not manually modify generated reports before evaluation.

Do not invent missing metrics.

Do not report estimated values as measured values.

Human annotations and automated evaluator results should be distinguishable.

Any failed run must remain part of the experiment record rather than being silently removed.

---

## 9. Before / After Comparison

Final experiment results will use the following structure:

| Metric | GPT Researcher Baseline | Enterprise Insight Agent | Improvement |
|---|---:|---:|---:|
| Evidence Coverage | TBD | TBD | TBD |
| Citation Correctness | TBD | TBD | TBD |
| Citation Completeness | TBD | TBD | TBD |
| Unsupported Claim Rate | TBD | TBD | TBD |
| Latency | TBD | TBD | TBD |
| Estimated Cost | TBD | TBD | TBD |

`TBD` values must only be replaced by real benchmark results.

---

## 10. Reproducibility Principle

Every reported improvement should be traceable to:

Benchmark Case  
→ Configuration  
→ Raw Execution  
→ Generated Report  
→ Evidence / Annotation  
→ Metric Calculation  
→ Before / After Result

This traceability chain is part of the engineering quality of the project.