# Final Benchmark Comparison Report

Date: 2026-09-07
Benchmark cutoff: 2026-09-05
Dataset: 12 cases — 8 development and 4 holdout

## Benchmark identity

This is a **same-version source-authority-weight ablation**, not a comparison with historical upstream GPT Researcher v3.6.1.

| Variant | `SOURCE_AWARE_AUTHORITY_WEIGHT` | Role |
|---|---:|---|
| Baseline | 0.0 | Semantic retrieval without authority contribution |
| Source-aware | 0.2 | The pre-existing source-aware candidate used in the completed experiment |

Both variants were produced from commit `9004478dc52b4ccdca4cc9bb03c6d86c3e6d1624`. The development and holdout manifests match on dataset hash, cutoff, effective settings, compression threshold, content limit, Python/package versions, timeout, and configuration after removing the intended authority-weight difference.

Quality metrics use the final human-reviewed, AI-assisted annotations under `QUALITY_ANNOTATION_RUBRIC_V1`. EI_001_A was the golden item-level calibration case. Required Units and the annotation protocol were frozen before variant review; all flagged and extreme cases passed the explicit human review gate.

Authority score is interpreted only as a **source-level reliability prior**. It is not factual correctness, claim confidence, or truth probability.

## Frozen micro-aggregation

The formal quality results in this report use the aggregation rule frozen before comparison:

```text
Evidence Coverage        = Σ supported_required_facts / Σ required_facts
Citation Correctness     = Σ supporting_citations / Σ evaluated_citations
Citation Completeness    = Σ claims_with_evidence / Σ factual_claims
Unsupported Claim Rate   = Σ unsupported_claims / Σ factual_claims
```

An individual report with zero evaluated citations contributes zero to both the Citation Correctness numerator and denominator. Its individual Citation Correctness remains `null`; it is never converted to zero.

## Development quality comparison

| Metric | Baseline numerator/denominator | Baseline | Source-aware numerator/denominator | Source-aware | Delta (SA − baseline) | Direction |
|---|---:|---:|---:|---:|---:|---|
| Evidence Coverage | 35/35 | 100.0000% | 35/35 | 100.0000% | +0.0000 pp | Tie |
| Citation Correctness | 405/482 | 84.0249% | 474/506 | 93.6759% | **+9.6510 pp** | Source-aware higher |
| Citation Completeness | 631/653 | 96.6309% | 629/657 | 95.7382% | −0.8927 pp | Baseline higher |
| Unsupported Claim Rate | 22/653 | 3.3691% | 28/657 | 4.2618% | +0.8927 pp | Baseline better because lower |

In the reviewed 8-case development split, w=0.2 produced substantially higher micro Citation Correctness while Required Unit coverage tied. It did not improve Citation Completeness or Unsupported Claim Rate.

## Holdout quality comparison

| Metric | Baseline numerator/denominator | Baseline | Source-aware numerator/denominator | Source-aware | Delta (SA − baseline) | Direction |
|---|---:|---:|---:|---:|---:|---|
| Evidence Coverage | 24/24 | 100.0000% | 24/24 | 100.0000% | +0.0000 pp | Tie |
| Citation Correctness | 208/219 | 94.9772% | 187/209 | 89.4737% | **−5.5035 pp** | Baseline higher |
| Citation Completeness | 347/360 | 96.3889% | 365/381 | 95.8005% | −0.5884 pp | Baseline higher |
| Unsupported Claim Rate | 13/360 | 3.6111% | 16/381 | 4.1995% | +0.5884 pp | Baseline better because lower |

In the reviewed 4-case holdout split, w=0.2 did not reproduce the development Citation Correctness gain. Required Unit coverage tied, while baseline was better on the other three micro metrics. The pre-existing weight remains unchanged; the holdout result is not used for tuning in this task.

## Per-case quality comparison

Values are `baseline → source-aware`. `SA` means source-aware wins, `B` means baseline wins, `T` means tie, and `N/A` means the pair is not mathematically comparable. Lower is better only for Unsupported Claim Rate.

| Case | Baseline review | SA review | Evidence Coverage | Citation Correctness | Citation Completeness | Unsupported Claim Rate |
|---|---|---|---|---|---|---|
| EI_001 | EI_001_A | EI_001_B | 1.0000 → 1.0000 T | 0.7308 → 0.9661 SA | 1.0000 → 0.9873 B | 0.0000 → 0.0127 B |
| EI_002 | EI_002_A | EI_002_B | 1.0000 → 1.0000 T | 0.8906 → 0.9434 SA | 0.9881 → 0.9200 B | 0.0119 → 0.0800 B |
| EI_003 | EI_003_A | EI_003_B | 1.0000 → 1.0000 T | 0.6377 → 0.9231 SA | 1.0000 → 0.9385 B | 0.0000 → 0.0615 B |
| EI_004 | EI_004_A | EI_004_B | 1.0000 → 1.0000 T | 0.9322 → 0.9839 SA | 0.9865 → 0.9878 SA | 0.0135 → 0.0122 SA |
| EI_005 | EI_005_B | EI_005_A | 1.0000 → 1.0000 T | 0.9545 → 0.9800 SA | 0.9398 → 0.9783 SA | 0.0602 → 0.0217 SA |
| EI_006 | EI_006_A | EI_006_B | 1.0000 → 1.0000 T | 0.8056 → 0.8140 SA | 0.9184 → 0.9756 SA | 0.0816 → 0.0244 SA |
| EI_007 | EI_007_B | EI_007_A | 1.0000 → 1.0000 T | 0.9429 → 0.8276 B | 0.9412 → 0.9222 B | 0.0588 → 0.0778 B |
| EI_008 | EI_008_B | EI_008_A | 1.0000 → 1.0000 T | 0.9744 → 0.9848 SA | 0.9855 → 0.9457 B | 0.0145 → 0.0543 B |
| EI_009 | EI_009_A | EI_009_B | 1.0000 → 1.0000 T | 0.9737 → 0.9615 B | 0.9608 → 0.9773 SA | 0.0392 → 0.0227 SA |
| EI_010 | EI_010_B | EI_010_A | 1.0000 → 1.0000 T | 0.9388 → null N/A | 0.9524 → 0.9512 B | 0.0476 → 0.0488 B |
| EI_011 | EI_011_B | EI_011_A | 1.0000 → 1.0000 T | 0.9375 → 0.9231 B | 0.9647 → 0.9565 B | 0.0353 → 0.0435 B |
| EI_012 | EI_012_B | EI_012_A | 1.0000 → 1.0000 T | 0.9608 → 0.8476 B | 0.9853 → 0.9496 B | 0.0147 → 0.0504 B |

## Win / loss / tie counts

### Development — 8 paired cases

| Metric | Source-aware wins | Baseline wins | Ties | N/A |
|---|---:|---:|---:|---:|
| Evidence Coverage | 0 | 0 | 8 | 0 |
| Citation Correctness | 7 | 1 | 0 | 0 |
| Citation Completeness | 3 | 5 | 0 | 0 |
| Unsupported Claim Rate | 3 | 5 | 0 | 0 |

### Holdout — 4 paired cases

| Metric | Source-aware wins | Baseline wins | Ties | N/A |
|---|---:|---:|---:|---:|
| Evidence Coverage | 0 | 0 | 4 | 0 |
| Citation Correctness | 0 | 3 | 0 | 1 |
| Citation Completeness | 1 | 3 | 0 | 0 |
| Unsupported Claim Rate | 1 | 3 | 0 | 0 |

Across all 12 cases, Evidence Coverage tied in every case. Citation Correctness was 7 SA wins, 4 baseline wins, and 1 unavailable pair; Citation Completeness and Unsupported Claim Rate were each 4 SA wins and 8 baseline wins. These counts are metric-specific and are not combined into a synthetic overall score.

## Operational comparison

These are observed values from the existing live executions. The runs were nondeterministic and were not paired deterministic performance trials, so the differences must not be interpreted causally.

### Development

| Operational metric | Baseline | Source-aware | Observed difference (SA − baseline) |
|---|---:|---:|---:|
| Mean latency | 250.0845 s | 231.5822 s | −18.5024 s |
| Total estimated cost | $4.204980 | $3.895348 | −$0.309633 |
| Mean estimated cost/case | $0.525623 | $0.486918 | −$0.038704 |
| Total source count | 118 | 111 | −7 |
| Mean source count/case | 14.750 | 13.875 | −0.875 |
| Total web search calls | 32 | 32 | 0 |
| Mean web search calls/case | 4.000 | 4.000 | 0.000 |
| Failures | 0 | 0 | 0 |
| Completed / completion rate | 8 / 100% | 8 / 100% | Tie |

### Holdout

| Operational metric | Baseline | Source-aware | Observed difference (SA − baseline) |
|---|---:|---:|---:|
| Mean latency | 270.3586 s | 259.5955 s | −10.7631 s |
| Total estimated cost | $2.204397 | $2.134025 | −$0.070373 |
| Mean estimated cost/case | $0.551099 | $0.533506 | −$0.017593 |
| Total source count | 64 | 57 | −7 |
| Mean source count/case | 16.000 | 14.250 | −1.750 |
| Total web search calls | 16 | 16 | 0 |
| Mean web search calls/case | 4.000 | 4.000 | 0.000 |
| Failures | 0 | 0 | 0 |
| Completed / completion rate | 4 / 100% | 4 / 100% | Tie |

It is defensible to say that lower latency, cost, and source counts were **observed in these particular source-aware runs**. It is not defensible to say that authority reranking caused those differences.

## Exact `benchmarks.compare` outputs

The command created two new JSON files without overwriting existing artifacts:

- `outputs/final-compare-dev`
- `outputs/final-compare-holdout`

The tool validates compatible manifests, terminal case coverage, baseline/source-aware roles, and the controlled configuration difference. It calculates cases, attempts, failures, failure rate, mean latency, reviewed-case count, total estimated cost, cost-known count, and unweighted per-report macro means for the four quality metrics. It does **not** calculate micro quality aggregates, source-count/search-call aggregates, deltas, per-case wins, completion rate as a separate field, or a synthetic overall score.

| Split / variant | Cases | Failures | Mean latency (s) | Total cost ($) | Macro Evidence Coverage | Macro Citation Correctness | Macro Citation Completeness | Macro Unsupported Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dev baseline | 8 | 0 | 250.0845368625 | 4.2049803400 | 1.0000000000 | 0.8585744884 | 0.9699239781 | 0.0300760219 |
| Dev source-aware | 8 | 0 | 231.5821663125 | 3.8953476000 | 1.0000000000 | 0.9278542490 | 0.9569191513 | 0.0430808487 |
| Holdout baseline | 4 | 0 | 270.3586391750 | 2.2043973800 | 1.0000000000 | 0.9526860086 | 0.9657913165 | 0.0342086835 |
| Holdout source-aware | 4 | 0 | 259.5955462750 | 2.1340248000 | 1.0000000000 | **null** | 0.9586484526 | 0.0413515474 |

The source-aware holdout macro Citation Correctness is unavailable because EI_010_A's individual value is null and `compare.py` requires every per-report value to be defined before taking a macro mean. The formal frozen micro result remains available at 187/209 = 89.4737%, because EI_010_A contributes zero to both integer sums. No null value was imputed.

## Interpretation

What improved in this reviewed benchmark:

- Development micro Citation Correctness increased by 9.6510 percentage points, with source-aware winning 7 of 8 development cases on that metric.
- Source-aware won Citation Completeness and Unsupported Claim Rate in three development cases and one holdout case.
- Required Unit coverage remained complete for both variants in both splits.

What did not improve:

- The development Citation Correctness gain did not generalize to holdout; source-aware was 5.5035 percentage points lower on the holdout micro aggregate.
- Citation Completeness was lower for source-aware by 0.8927 points on dev and 0.5884 points on holdout.
- Unsupported Claim Rate was higher for source-aware by 0.8927 points on dev and 0.5884 points on holdout.
- Per-case Citation Completeness and Unsupported Claim Rate favored baseline in 8 of 12 cases.
- Operational differences are observations from nondeterministic live runs, not causal effects of reranking.

The evidence therefore supports a mixed result: w=0.2 improved citation support quality on development, but the improvement did not hold on the four-case holdout and came with slightly weaker claim-level support metrics in both splits. No production-wide or universal accuracy claim is warranted.

## Limitations

- The benchmark contains only 12 cases, including a four-case holdout.
- Live web results are not a fixed corpus; search and generated reports are nondeterministic.
- Quality annotations are human-reviewed and AI-assisted, not an independent double-blind multi-reviewer study.
- Citation Correctness measures whether saved sources support cited propositions; it does not establish real-world truth.
- Evidence Coverage is saturated at 100% for both variants, limiting discrimination on this dataset.
- The two variants have different report-level citation and claim denominators, making the frozen micro formulas important and ruling out casual comparison of raw counts.
- EI_010_A has no explicit body Markdown citation links. Its author–year references are excluded by the frozen protocol, making individual Citation Correctness null.
- The pre-existing w=0.2 candidate was not tuned in this final comparison and should not be declared optimal from these results.

## Resume-safe benchmark claims

- On this 12-case same-version benchmark, both baseline and source-aware achieved 100% micro Evidence Coverage of the frozen Required Units.
- In the reviewed 8-case development split, source-aware w=0.2 achieved 93.68% micro Citation Correctness versus 84.02% for baseline, a +9.65 percentage-point observed difference.
- In the reviewed 4-case holdout split, source-aware achieved 89.47% micro Citation Correctness versus 94.98% for baseline, a −5.50 percentage-point observed difference; the development gain did not reproduce on holdout.
- Source-aware Citation Completeness was 95.74% on development and 95.80% on holdout, compared with 96.63% and 96.39% for baseline.
- All 24 report variants were scored from final human-reviewed, AI-assisted annotations with exact report-hash binding and no missing annotations.
- The benchmark demonstrates an evidence-reliability ablation and reproducible evaluation workflow; it does not establish universal factual-accuracy or causal performance improvement.

## Validation and integrity

- Baseline/source-aware mapping was independently verified by run ID, report hash, variant, and manifest.
- Development has exactly 8 unique paired cases; holdout has exactly 4; no case is duplicated or missing.
- Every micro numerator and denominator was recomputed directly from final per-report integer annotations and reconciles with the reported ratios.
- Every per-case metric reconciles with the scored results.
- Operational values reconcile with the scored and raw records.
- EI_010_A null handling was verified; no zero imputation occurred.
- Both `benchmarks.compare` output files exist and parse as same-version ablation results.
- Pre/post tree hashes show the four raw benchmark directories and four scored input directories were unchanged.
- v3 claim, citation, Required Unit, and summary ledgers were not modified.
- No live benchmark was rerun.
- No live web access was used.
- No commit or push was performed.
- `git diff --check`: PASS (no output).
- `git status --short`: `?? benchmarks/annotations/`

The comparison files and this report are under ignored `outputs/` and `my-docs/` paths. The only visible Git worktree addition remains the previously created `benchmarks/annotations/` directory.
