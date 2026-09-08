# Enterprise Insight Benchmark V2 — Frozen Protocol

**Protocol:** `enterprise-insight-bench-v2/2.0.0`

**Status:** FROZEN

**Dataset:** `benchmarks/dataset/enterprise_insight_bench_v2.json`

**Information cutoff:** 2026-09-05
**Frozen on:** 2026-09-08

This protocol was frozen before V2 implementation and final comparison. It is independent
of the immutable V1 dataset, annotations, runs, and results. Any semantic change requires a
new version and hash; unfavorable cases or results may not be removed.

## 1. Cases and split

The dataset contains 30 unique cases: five in each of the six frozen categories. Each
category contributes three development cases and two holdout cases, producing 18 development
and 12 holdout cases. Category labels, split, cutoff, query, Required Units, evidence-strength
rules, and applicable high-risk types are frozen. Development may be used for debugging and
one documented policy revision before the final freeze; this version is that final freeze.
Holdout may be executed only in the final locked comparison and may not drive tuning.

The cutoff applies to the state of the world claimed in a report. A source published after
the cutoff is excluded even if it describes an earlier event, unless it is retained only as
explicitly labeled audit metadata and never used for scoring or generation. Unknown dates
fail strict freshness rules and are flagged for other modes.

## 2. Paired candidate fixture

For each case, retrieve one candidate evidence pool once under a recorded retrieval query,
cutoff, provider/configuration, timestamp, and budget. Preserve raw candidates, normalized
provenance, publication-date observations, independence-group IDs, failures, and a canonical
SHA-256. Baseline, V1, and V2 selection operate on that identical immutable pool.

This paired fixture reduces search variance; it does not remove embedding, model, or report
generation nondeterminism. Retrieval-stage metrics and end-to-end report metrics are reported
separately. Historical V1 runs are not rerun or rewritten: the `v1` label here means the
frozen fixed-weight behavior applied to the new V2 fixture as a same-codebase ablation.

Each final variant/case is attempted exactly once. A provider failure remains a failure;
there is no cherry-picking or retry-until-success. Provider-internal retries already present
in the stack are recorded where observable.

## 3. Variants

- `baseline`: semantic-only selection, `authority_weight=0`, no task-aware policy, no claim
  gate, no grounding validator.
- `v1`: fixed source-aware selection, `authority_weight=0.20`, no task-aware policy, no claim
  gate, no grounding validator. The weight is not claimed globally optimal.
- `v2`: frozen query-aware policy, evidence-gated claims, and post-generation grounding
  validation.

All non-variant controls—candidate hash, code commit, model/provider, prompts except the
mechanism under ablation, temperature, token limits, embedding configuration, and timeout—
must match or be reported as an invalid comparison.

## 4. Annotation protocol

Before bulk annotation, reviewers calibrate on at least one development report from each
category. The calibration set must cover claim segmentation, citation support, Required Unit
scoring, evidence strength, independence, freshness, and all high-risk types present.

For every report, preserve the report SHA-256, raw output, candidate/selection hashes,
scoring input, reviewer identity, rubric version, item-level decisions, ambiguity flags,
and adjudication. The reviewer:

1. segments atomic externally verifiable factual claims;
2. maps inline citations to exact candidate evidence;
3. marks support/conflict/unclear using scope, entity, and cutoff;
4. scores each frozen Required Unit and its required strength;
5. labels high-risk types and rule satisfaction;
6. identifies independent publisher/organization groups;
7. records the authority prior only for evidence with a valid support link;
8. flags ambiguity rather than silently resolving it.

AI assistance is permitted, but every ambiguity, extreme score, failed run, and high-risk
violation requires human adjudication. Reviewers may use only the frozen candidate pool and
protocol; no silent external evidence is allowed. Blind variant labels are preferred.

## 5. Frozen quality metrics

All headline aggregates are micro-aggregates over the entire declared split. Per-case and
per-category values are also retained. Zero denominators are `null`, never imputed. A final
comparison is invalid if any completed report lacks a reviewed annotation.

- **Citation Correctness** = supporting evaluated citation links / evaluated citation links.
- **Citation Completeness** = factual claims with at least one valid supporting evidence
  link / factual claims.
- **Unsupported Claim Rate** = `1 - Citation Completeness`; it is a derived diagnostic, not
  an independent headline metric.
- **Strong Evidence Coverage** = frozen Required Units satisfied at their declared
  `evidence_strength_rule` / all frozen Required Units. Partial topical mention does not pass.
- **Source Reliability Score** = sum of authority priors for distinct normalized source
  records that have at least one valid supporting claim link / count of those distinct
  supporting source records. Multiple chunks or links from the same normalized source count
  once per report. Retrieved-but-unused, conflicting, unclear, and merely listed URLs are
  excluded.
- **High-Risk Claim Corroboration Rate** = emitted high-risk factual claims satisfying every
  applicable frozen risk rule / all emitted high-risk factual claims. One claim with multiple
  types is one denominator item and must satisfy the strictest applicable rule.
- **Task Classification Accuracy** = cases whose predicted category exactly matches the
  frozen category / all 30 cases. Missing predictions are incorrect.
- **Category Robustness** = the complete vector of Citation Correctness, Citation
  Completeness, Strong Evidence Coverage, Source Reliability Score, High-Risk Corroboration,
  and failure rate for each category; no synthetic average hides a weak category.
- **Generalization Gap** for metric `m` = `development_m - holdout_m`; both signed and absolute
  values are reported. Lower-is-better engineering metrics retain their natural direction.

Engineering metrics—latency, provider cost, source count, search calls, failure rate, and
token usage—are reported separately and never combined with quality into one score.

Failed runs remain in attempted-case and failure denominators. Their Required Units count as
unsatisfied. Claim/citation metrics cannot be invented for an absent report, so the split
metric is `null`; the final quality gate therefore fails. Classification may still be scored
if the pre-retrieval prediction was durably recorded.

## 6. Quantitative acceptance and predefined failure conditions

V2 passes only if every condition below is met on the single final locked experiment. The
five core comparison dimensions are Citation Correctness, Citation Completeness, Strong
Evidence Coverage, Source Reliability Score, and High-Risk Claim Corroboration Rate.

| Gate | Frozen threshold |
|---|---:|
| completed and fully annotated holdout cases | 12 / 12 |
| holdout Citation Correctness relative to paired baseline | strictly greater |
| holdout Citation Completeness relative to paired baseline | greater than or equal |
| holdout Strong Evidence Coverage relative to paired baseline | strictly greater |
| holdout Source Reliability Score relative to paired baseline | strictly greater |
| holdout High-Risk Claim Corroboration relative to paired baseline | strictly greater |
| improved core dimensions relative to paired baseline | at least 4 of 5 |
| maximum regression in the remaining core dimension | 0.01 absolute (1 percentage point) |
| holdout Citation Correctness | >= 0.90 |
| holdout Citation Completeness | >= 0.97 |
| holdout Strong Evidence Coverage | >= 0.85 |
| holdout Source Reliability Score | >= 0.75 |
| holdout High-Risk Claim Corroboration Rate | >= 0.90 |
| all-case Task Classification Accuracy | >= 0.90 |
| mean absolute dev-to-holdout gap across five core metrics | at least 0.01 lower than paired baseline |
| severe per-category regression versus paired baseline | none greater than 0.05 absolute |

Predefined hard failures are:

- **material regression:** the one allowed non-improving core dimension is more than 0.01
  below paired baseline on holdout, or more than one core dimension fails to improve;
- **severe category regression:** for any category and core metric, V2 is more than 0.05
  below paired baseline on the same split. Absolute category floors remain Citation
  Completeness 0.85, Strong Evidence Coverage 0.75, and High-Risk Corroboration 0.80;
- **generalization failure:** V2 mean absolute dev/holdout gap across the five core metrics
  is not at least 0.01 lower than paired baseline. A `null` gap is a failure;
- any missing/changed case, incompatible fixture hash, unreviewed completed report, missing
  raw artifact, post-cutoff scored evidence, nonterminal run, fabricated metric, or holdout
  tuning.

Passing aggregate thresholds cannot override a hard failure. The experiment is allowed to
conclude that V2 failed. Paired Baseline and V1 are evaluated on the new frozen V2 fixture;
historical V1 values are never backfilled into missing V2-fixture metrics.

## 7. Cost and execution controls

All schema, CLI, fixture, hashing, scoring, and synthetic/offline tests must pass before any
paid call. The initiating V2 delivery request is the authorization for one locked experiment;
it does not authorize retries or unrelated paid work. The run manifest must declare a hard
USD 75 cap and a USD 60 stop-review threshold. No new case starts after the threshold without
renewed authorization. Record actual estimated cost, model tokens, search calls, and failures
per case and variant. Paid live runs are never a debugging mechanism.

Run outputs are append-only, uniquely named, and never overwrite V1 or another run. The final
comparison locks commit SHA, dataset SHA-256, spec versions, candidate fixture hashes,
configuration, environment/package versions, and annotation rubric. Raw and annotation
artifacts are retained even when the result is unfavorable.
