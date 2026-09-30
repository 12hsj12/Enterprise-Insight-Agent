# V2 holdout: one-pass execution and validity review

**Run date:** 2026-09-30

**Source commit:** `d6cb50f7d6a3b840d5eacf5e1986a7eb9ada1cf2` on `feat/evidence-v2`

**Frozen dataset SHA-256:** `95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`

**Protocol and cutoff:** `enterprise-insight-bench-v2/2.2.0`, 2026-09-05

**Raw artifacts:** [`outputs/v2-holdout-final-20260930-d6cb50f7`](../../outputs/v2-holdout-final-20260930-d6cb50f7/) (local, ignored by Git)

## Decision

The 12 specified holdout cases were each submitted **once** through the real V2 Enterprise API. All 12 completed and produced a report, execution record, trace, task response, retrieval capture, runtime evaluation record, and verified artifact hashes. No code, prompt, parameter, policy, dataset, or benchmark rule was changed during the run. No holdout-based tuning or quality rerun occurred.

**This run is not a valid final frozen V2 benchmark result.** It is a complete one-pass V2 holdout execution with useful failure evidence. The frozen protocol requires item-level reviewed annotations for all completed reports, a paired Baseline/V1/V2 comparison on a shared eligible candidate fixture, and cutoff-safe scoring. This run is V2-only, has no completed human adjudication of the 36 holdout Required Units or claim/citation links, and has observed cutoff-compatibility concerns. Do not substitute runtime Gate/Grounding counters for those missing quality scores or claim final acceptance.

## Execution integrity and stability

| Measure | Observed result |
|---|---:|
| Holdout IDs attempted, unique, completed | 12 / 12 / 12 |
| Case-level failures or quality reruns | 0 / 0 |
| Reports, executions, traces and hashes present and verified | 12 / 12 |
| Candidate-capture errors | 0 |
| Holdout category predictions matching frozen labels | 12 / 12; not the frozen all-30 accuracy metric |
| Selected evidence chunks | 370; chunks are not unique sources |
| Mean case duration | 331.344 seconds |
| Full sequential wall time | 3,976.522 seconds |
| Runtime estimated provider cost | USD 21.27184002; invoice amount unavailable |

The run used the same request construction as the existing development operator path: full frozen query in `target`, `Development research` in `topic`, frozen Required Unit descriptions in `dimensions`, cutoff `2026-09-05`, and both V2 flags enabled. The effective models were `openai:deepseek-v4-flash` for fast/smart/strategic calls and `huggingface:sentence-transformers/all-MiniLM-L6-v2` for embeddings; search was Tavily. The run manifest recorded a USD 60 stop-review threshold and USD 75 hard cap. The estimate stayed below both. Provider billing and token totals are unavailable. The request topic is recorded for reproducibility; it was not altered after seeing outputs.

The [manifest](../../outputs/v2-holdout-final-20260930-d6cb50f7/manifest.json) records one attempt per ID and the locked configuration. Each case directory contains `case_input.json`, `request.json`, `task.json`, `candidate.json`, `selected.json`, `scoring.json`, `evaluation.json`, `report.md`, `execution.json`, `trace.json`, and `artifact_hashes.json`. The [diagnostic audit](../../outputs/v2-holdout-final-20260930-d6cb50f7/evaluation_diagnostics.json) is a deterministic summary of those files; it explicitly leaves unreviewed formal quality metrics null.

## Quality dimensions

| Dimension | Result and limit |
|---|---|
| User Utility | Qualitative case review below. The frozen V2 dataset does not define a numerical User Utility metric or a score threshold, so none was invented after holdout exposure. Reports often address the requested headings but are long and difficult to use directly. |
| Answer-Critical Claim quality | Runtime reported 1,450/1,450 answer-critical units reviewed and 0 `answer_critical_unsupported_strong_claims`. This is an internal diagnostic, not an independent correctness rate. Review found potentially overstrong conclusions and premise gaps described below. Atomic claim segmentation and citation-support adjudication are incomplete. |
| Evidence Reliability | Uneven. First-party Microsoft/Kubernetes material appears in some cases; both competitive-comparison cases lack a balanced first-party source set. Sources with metadata after the cutoff occur in 10 report bodies, and six cases have at least one such source linked to a runtime `LIMITED` unit. The frozen Source Reliability Score is null because valid supporting links and distinct normalized supporting sources have not been independently reviewed. |
| Strict RU | The denominator is the frozen 36 units, three per case. The runtime `COVERED` label is not a strict `SATISFIED` adjudication. No 36-item human-reviewed annotation ledger was completed, so Strict RU is **N/A**, not 0/36 or a guessed percentage. It remains diagnostic only. |

The 12 reports together contain 447,695 characters and 678 occurrences of the two repeated qualification prefixes beginning “Current evidence does not establish” or “The cited sources support the following claim”. Runtime audit records contain 33 `VERIFIED`, 231 `LIMITED`, and 1,210 `UNRESOLVED` units; these are implementation states, not independent claim-quality or Strict RU scores. The prefixes often appear inside paragraphs and tables, increasing reading burden and sometimes leaving an unsupported assertion visible after a warning.

## Six-category review

This is a bounded, AI-assisted review of the saved reports and selected evidence. It does not replace the frozen item-level human annotation protocol. Every category has two completed cases.

| Category | Cases | User-facing and evidence observation |
|---|---|---|
| Factual Verification | FV_004, FV_005 | FV_004 separates SSO, audit, and compliance, but its high-confidence SSO conclusion relies on secondary summaries, a Claude **Code** Enterprise source for a Claude Enterprise question, and an inferred Anthropic documentation trail absent from the saved pool. FV_005 uses substantial Microsoft first-party material and explains abuse monitoring and approval options; its description of `ContentLogging=false` as the default is stronger than the saved excerpt, which only displays a JSON value without enough surrounding context to establish a platform-wide default. |
| Technical / Capability Analysis | TC_004, TC_005 | TC_004 distinguishes core Gateway API from its inference extension and external components, with Kubernetes/Istio material and no late-dated selected source detected. TC_005 describes batching and KV-cache tradeoffs, but its runtime audit has zero `VERIFIED` units and uses a source updated after the cutoff in a `LIMITED` unit. Mechanism coverage does not establish the frozen source-strength rules. |
| Competitive Comparison | CC_004, CC_005 | CC_004 contains comparisons but its cited pool is dominated by third-party tool roundups and lacks direct GitHub/Cursor documentation for governance claims. CC_005 has only five selected chunks, including an Arize-authored comparison page updated after cutoff; it leaves a material Phoenix license conflict unresolved. Neither is a dependable procurement comparison as written. |
| Trend / Market Intelligence | TM_004, TM_005 | Both discuss requested trends and uncertainty, but both bring post-cutoff updated material into `LIMITED` output. TM_004 mixes evidence of general AI adoption with claims about small-model adoption. TM_005 usefully distinguishes forecasts from historical observations in places, yet the market-size and GPU-provider material has incompatible definitions and an after-cutoff updated source in claim-linked output. |
| Conflict & Credibility Resolution | CR_004, CR_005 | CR_004 presents Microsoft's boundary language and exceptions from first-party documents, but an independent adjudicator for the frozen conflict-strength rule is not established. CR_005 juxtaposes Pinecone marketing with third-party and competitor benchmarks; the experiments differ in scale, tier, recall and latency definitions, so its conclusion that workload settings are the predominant explanation is stronger than a paired reproducibility test would warrant. |
| Enterprise Decision / Recommendation | ED_004, ED_005 | Both offer conditional advice or a roadmap. ED_004's governed-core recommendation relies in part on CodeWave and other sources updated after cutoff; its categorical claims about the cheapest or only defensible configuration are not established by the saved evidence. ED_005 supplies a staged roadmap, but most cited source dates are unknown and its strict dependency-chain claim is more definite than the evidence supports. Neither is ready for an enterprise decision without source-level review. |

## Issue attribution

| Type | Observed issue |
|---|---|
| **SYSTEM ISSUE** | Cutoff handling is insufficient for the frozen scoring rule: source metadata showing publication or update after 2026-09-05 appears in ten report bodies. Six cases (TC_005, CC_004, CC_005, TM_004, TM_005, ED_004) have such sources linked to at least one runtime `LIMITED` unit. Some may be displayed as caveats rather than accepted facts, but `LIMITED` is generated report content, not merely separately retained audit metadata. FV_004's SSO confidence and FV_005's logging-default inference illustrate that internal zero-unsupported counters do not independently validate semantics. |
| **EVIDENCE LIMITATION** | Search/scraping returned blocked, empty, or timed-out pages; CC_005 retained only five selected chunks. Several cases rely on undated or secondary sources, competitor-authored comparisons, or incomparable performance benchmarks. These gaps must remain gaps under the one-pass protocol. |
| **PRESENTATION ISSUE** | The 678 repeated warning prefixes and very long reports obscure conclusions. English prose answers Chinese requests; warnings are inserted into table cells and source quotations, reducing scanability. Conditional recommendations sometimes remain prominent after their factual premises are flagged as unestablished. |

The cutoff audit uses saved `publication_date` and `updated_date` fields. A later update does not prove that every quoted sentence was first published later; it means the pre-cutoff version is unverified in the frozen candidate record. The six-case `LIMITED` finding is therefore a protocol-compatibility concern, not a claim that every affected statement is factually false. FV_004 and CR_005 mention late metadata in report bodies without a claim-input link to those records; they are not included in the six claim-linked cases.

## Frozen acceptance status

The frozen five headline quality metrics—Citation Correctness, Citation Completeness, Strong Evidence Coverage, Source Reliability Score, and High-Risk Claim Corroboration—are **null** for this run. The same is true of the formal Strict RU diagnostic. The 12 reports have no completed item-level, human-adjudicated holdout annotations; there is no paired Baseline/V1 result on the shared candidate fixture; and the cutoff audit raises compatibility concerns. The frozen 12/12 *completed and fully annotated* condition is therefore not met even though execution completion is 12/12. The comparison thresholds, all-30 classification threshold, and dev-to-holdout generalization gap cannot be evaluated.

**Conclusion:** the system ran stably on unseen holdout tasks, but the evidence does not establish reliable generalization of answer quality or source reliability. This one-pass observation should be retained as an unfavorable, audit-ready holdout execution. It is **insufficient as the final frozen experimental result**. Do not tune on these cases, rerun them for a favorable outcome, infer missing metrics from runtime diagnostics, or declare V2 qualified from this execution.
