# Six-Case Development Calibration Delivery

## Decision

**READY_FOR_HUMAN_REVIEW** — calibration itself is not complete. All human decisions remain pending.

## Code State

Branch: `feat/evidence-v2`. Start: `66bc12567869a2d218bd72078dd3fb4d92152da2` (clean, fetched, 0/0).
Execution code checkpoint: `fa385086` (pushed). Minimal observation capture was required; this delivery document is committed in the subsequent material checkpoint. The final response records its exact HEAD and synchronization result.

## Readiness Preflight

| Material | Readiness |
|---|---|
| Case/query/18 Required Units/cutoff | Existing frozen case metadata, verified unchanged |
| Report + SHA-256 | Existing workflow export, preserved actual bytes |
| Candidate pages/eligible chunks | Minimal opt-in capture; upstream stages distinct, bounded text + provenance/query and hash |
| Selected evidence | Existing result objects exported separately, 191 chunks trace to candidate |
| Scoring | Existing similarity/reliability/ranking diagnostics only, no new scoring |
| Claims/links/qualifications/Gate/generated records/Grounding/repair | Existing execution.json; no semantic changes |
| Citation mapping and excerpts | Derived from actual generated records and saved selected evidence |
| Trace | Existing run/trace IDs and exports, plus saved diagnostics |
| Billing / tokens / absent source metadata | Actual billing/token totals unavailable; unknown source metadata explicitly unresolved |

## Development Runs

Every case completed once (HTTP 200). Configuration: `openai:deepseek-v4-flash`, TavilySearch, `huggingface:sentence-transformers/all-MiniLM-L6-v2`. Full timing and search counters are in the manifest; 4 observed search calls per case. No quality retries.

| Case / category | Task/run ID | Report / candidate / selected / scoring / execution / trace | Runtime USD estimate |
|---|---|---|---:|
| EIV2_FV_001 / factual_verification | `01b87b35-114e-49a3-9bf0-e551afd61a75` | [report](factual_verification/EIV2_FV_001/report.md) / [selected](factual_verification/EIV2_FV_001/selected.json) / [scoring](factual_verification/EIV2_FV_001/scoring.json) / [execution](factual_verification/EIV2_FV_001/execution.json) / [trace](factual_verification/EIV2_FV_001/trace.json) / [candidate](../../../../outputs/calibration-six-20260911/EIV2_FV_001/candidate.json) | 0.47405992 |
| EIV2_TC_001 / technical_capability_analysis | `993797f0-7184-44b4-b0cf-8f0d390c530f` | [report](technical_capability_analysis/EIV2_TC_001/report.md) / [selected](technical_capability_analysis/EIV2_TC_001/selected.json) / [scoring](technical_capability_analysis/EIV2_TC_001/scoring.json) / [execution](technical_capability_analysis/EIV2_TC_001/execution.json) / [trace](technical_capability_analysis/EIV2_TC_001/trace.json) / [candidate](../../../../outputs/calibration-six-20260911/EIV2_TC_001/candidate.json) | 0.60045590 |
| EIV2_CC_001 / competitive_comparison | `8b1f6902-92b1-40be-af1a-749e6a431b45` | [report](competitive_comparison/EIV2_CC_001/report.md) / [selected](competitive_comparison/EIV2_CC_001/selected.json) / [scoring](competitive_comparison/EIV2_CC_001/scoring.json) / [execution](competitive_comparison/EIV2_CC_001/execution.json) / [trace](competitive_comparison/EIV2_CC_001/trace.json) / [candidate](../../../../outputs/calibration-six-20260911/EIV2_CC_001/candidate.json) | 0.53648820 |
| EIV2_TM_003 / trend_market_intelligence | `f7246966-5232-4274-97d5-d4b3b3e976ac` | [report](trend_market_intelligence/EIV2_TM_003/report.md) / [selected](trend_market_intelligence/EIV2_TM_003/selected.json) / [scoring](trend_market_intelligence/EIV2_TM_003/scoring.json) / [execution](trend_market_intelligence/EIV2_TM_003/execution.json) / [trace](trend_market_intelligence/EIV2_TM_003/trace.json) / [candidate](../../../../outputs/calibration-six-20260911/EIV2_TM_003/candidate.json) | 0.63643392 |
| EIV2_CR_003 / conflict_credibility_resolution | `b2dadf7b-8489-439b-a7b5-9c9191b708f1` | [report](conflict_credibility_resolution/EIV2_CR_003/report.md) / [selected](conflict_credibility_resolution/EIV2_CR_003/selected.json) / [scoring](conflict_credibility_resolution/EIV2_CR_003/scoring.json) / [execution](conflict_credibility_resolution/EIV2_CR_003/execution.json) / [trace](conflict_credibility_resolution/EIV2_CR_003/trace.json) / [candidate](../../../../outputs/calibration-six-20260911/EIV2_CR_003/candidate.json) | 0.55273960 |
| EIV2_ED_002 / enterprise_decision_recommendation | `43179a06-7c15-47f2-a1f8-fec242a5f1f4` | [report](enterprise_decision_recommendation/EIV2_ED_002/report.md) / [selected](enterprise_decision_recommendation/EIV2_ED_002/selected.json) / [scoring](enterprise_decision_recommendation/EIV2_ED_002/scoring.json) / [execution](enterprise_decision_recommendation/EIV2_ED_002/execution.json) / [trace](enterprise_decision_recommendation/EIV2_ED_002/trace.json) / [candidate](../../../../outputs/calibration-six-20260911/EIV2_ED_002/candidate.json) | 0.88105254 |

CC and CR completed with zero emitted records. FV/TC/TM/ED emitted 3/10/19/8 records respectively. Records are further segmented for review; omitted plan claims are not report claims.

## Artifact Integrity

All per-case artifact hashes were recomputed from actual bytes; see VALIDATION.json for the final count. All 191 selected chunks match candidate query, URL and content. Report hashes match the original execution hash. Case → run → report → evidence → citation mapping → review sheet → hash → trace links resolve. Root ARTIFACT_HASHES.json additionally covers the review-package files.

Dataset SHA-256 verified: `95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`.

## Risk Coverage

Covered: `numeric_value`, `release_status_availability`, `comparative_claim`, `benchmark_or_performance`, `conflict_sensitive_claim`.
Not covered: `date_or_time_window`, `market_metric`, `superlative_or_ranking`. These are reported gaps, not reasons to add holdout cases.

## AI-assisted Pre-annotation

| Item | Count |
|---|---:|
| Proposed atomic factual Claims | 115 |
| Non-factual recommendation segments | 3 |
| Claim/citation pairs | 184 |
| Required Units | 18 |
| Evidence-strength items | 45 |
| Independence items | 45 |
| Freshness items | 45 |
| High-risk items | 28 |

All items preserve AI_ASSISTED_RECOMMENDATION, reasons, exact saved text and human fields. No FINAL_LABEL is written. Fragment segmentation retains parent text and runtime Claim ID for interpretation.

## Human Review Queue

The complete 483-item AI-assisted ledger remains intact. Human work is compressed
to 87 tasks: 51 representative calibration-core tasks and 36 adjudication tasks.
The latter comprise 34 parent-report semantic bundles covering all 203 flagged
segmentation/citation/high-risk ledger records, plus one publisher-relationship
independence decision and one genuinely disputed date-attribution decision. All 18 Required Units remain directly reviewable in the
calibration core. Missing dates, unavailable source organizations, domain-only
differences and unqualified primary status remain deterministic ledger outcomes,
not separate confirmation tasks. No recommendation changed and all human fields
remain null.

## Calibration Manifest

`human_review_status = PENDING`; `reviewer = null`. `package_status = READY_FOR_HUMAN_REVIEW`, not calibration complete.

## Cost

Six-case runtime accumulated estimate: **USD 3.68123008**. Actual provider invoiced amount: **unavailable**, stored as null. Actual token usage: unavailable. Search billing is not included in a reconciled total. Official benchmark cost: **USD 0**.

## Tests and Independent Review

For this compression checkpoint, 143 focused/regression tests passed (3 warnings,
22.52 s): the new queue compression tests plus capture, Batch 8 enterprise
integration/evaluation, qualification integration, Trace, Evaluation, frozen
benchmark, source-aware ranking, API/persistence, ClaimGate and Grounding. Offline
package verification also passed: 78 per-case hashes, 191 selected/candidate
matches, 483 ledger items, 87 human tasks and all 18 Required Units. No unrelated
broad-suite repair was attempted.
Independent review verified all then-existing 72 hashes, 483 unique review IDs, exact spans/excerpts, 184 citation links, 19 explicit date excerpts, 191 selected-to-candidate mappings and all 18 Required Units. Additional diagnostics exports are included in final hash validation. This is engineering integrity review, not human gold adjudication.

## Frozen Contract Check

Six development cases only; official holdout executions = 0. No holdout report was opened for evaluation, annotated or tuned against. Dataset, split, Required Units, cutoff, rubric, classifier, Evidence/Claim/Binder, qualification, Gate and Grounding semantics unchanged. V1 untouched. No Baseline runner, paired replay, final comparison or new adjudicator semantics.

## Next Step

Human reviewer reviews the compressed calibration core and adjudication queue.
