# V2 Utility Correction Batch 5 Final Valid Delivery

## Decision

The new six-case development result set is **execution-valid but does not establish V2 effectiveness**. All six cases generated evaluable final reports on their first attempt. Strict Required Unit coverage rose from **1/18 (5.6%) to 2/18 (11.1%)**, a gain of one unit. The priority CC comparison is still nearly empty, CR does not present the two disputed scores, and ED does not give a migration recommendation. Manual report inspection also found factual and temporal safety defects. These are quality findings, not a deterministic report-generation blocker.

None of the three prescribed final recommendation tokens applies without misrepresenting the evidence: both freeze options require material utility and no serious factual leakage, while `STOP_AND_REVIEW_ONE_DETERMINISTIC_BLOCKER` is reserved for a code error that prevents normal report generation. The batch stops here for operator review. No holdout or repair was started.

## Experiment Validity

- Branch: `feat/evidence-v2`; frozen accepted Agent runtime: `4116f4f7ae9703d6e35e8555417e81b8adc150cf`; HEAD at start: docs-only `17d14254`.
- `git diff 4116f4f7 HEAD -- gpt_researcher backend scripts tests` was empty, and the tracked worktree was clean before execution. The ignored local operator guard did not change the request, Agent runtime, Gate, Grounding, prompt, retrieval strategy, threshold, or frozen rubric.
- Dataset SHA-256: `95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`; benchmark schema: `enterprise-insight-bench-v2/2.2.0`; information cutoff: `2026-09-05`.
- Every saved task request has `enable_v2_execution=true` and `enable_v2_evidence_selection=true`.
- Formal run IDs, in order: FV `4e9e96cf-81cd-4804-8247-e893b5269845`; TC `2c788f44-9491-4b14-9310-0b76172ce626`; CC `0e0bcf6e-f209-45ce-8f60-617968a74278`; TM `1162b995-096a-432b-aeb1-6cae60776583`; CR `1e8e9e89-b7a2-49a6-867b-391c579c1041`; ED `41509594-2f5b-4e9c-a7cc-2e4a03263f70`.
- All six returned HTTP 200 with completed task, report, execution record and trace. Infrastructure failures: **0**. Infrastructure retries: **0**. Selective or quality reruns: **0**. The invalid earlier Batch 5 runs, diagnostic TC, post-fix TC smoke, timeout FV and balance-blocked FV are excluded.
- Official holdout runs, searches, evaluations and tuning: **0** each.
- Raw task, candidate, selected-evidence, execution, trace and report artifacts are preserved in ignored `outputs/batch5-final-valid-20260916/formal_results/`. This delivery cites those artifacts; it does not promote generated provider data into Git.

## Strict RU

Before: **1/18 = 5.6%**. After: **2/18 = 11.1%**. Delta: **+1/18 = +5.6 percentage points**. The frozen strength rule and substantive final-report coverage were applied without partial credit. A runtime `COVERED` label is not automatically a strict `SATISFIED` decision.

| Case | After | Required Unit judgments and reason |
| --- | ---: | --- |
| FV_001 | **1/3** | `training_default` SATISFIED: a saved OpenAI first-party statement supports default no-training. `exceptions` NOT_SATISFIED: the report presents abuse monitoring and legal retention as exceptions to *no-training*, omitting the distinct customer opt-in/feedback exception. `retention` NOT_SATISFIED: it covers controls, but the 30-day assertion relies on a mirror and one relevant secondary source; another cited article's “30 days” refers to Anthropic, not OpenAI. The full retention obligation is not supported at the frozen strength. |
| TC_001 | **0/3** | `hybrid` NOT_SATISFIED: the first-party documentation is about AlloyDB's built-in hybrid function, and pgvector's own mechanism lacks the required first-party plus independent support. `indexes` NOT_SATISFIED: the report explicitly says evidence is insufficient. `limits` NOT_SATISFIED: it discusses access control and transactional consistency but misses scale, filtering, concurrency and operational limitations required by the unit. |
| CC_001 | **0/3** | `model_choice`, `governance_network`, and `pricing` are all NOT_SATISFIED: the report contains only four repeated insufficient-evidence placeholders and no two-sided comparison. |
| TM_003 | **1/3** | `regions` NOT_SATISFIED: Oracle/Middle East material does not establish expansion across major cloud AI services. `models` SATISFIED: pre-cutoff, distinct Bits Lovers, Crux Digits and EPC Group material supports multi-model offerings across AWS, Azure and Google, and the report substantively covers this trend. `controls` NOT_SATISFIED: generic AI/data governance product descriptions do not establish the requested trend in major cloud providers' generative-AI controls. |
| CR_003 | **0/3** | `vendor_score` NOT_SATISFIED: no official AIME 2024 score appears. `replication` NOT_SATISFIED: no third-party replication score appears. `explanation` NOT_SATISFIED: without both results and an independent adjudicator, the conflict is not evaluated. |
| ED_002 | **0/3** | `capabilities` NOT_SATISFIED: the comparison rests on one unqualified secondary article, not first-party plus independent support. `operations` NOT_SATISFIED: the same article is the only cited source for operational claims, not two independent sources. `migration` NOT_SATISFIED: there is no conditional recommendation. |

## User Utility

- **FV:** Useful default policy and retention-control explanation, but the conflation of training opt-in with abuse/legal retention can mislead an enterprise reader.
- **TC:** Explains one practical hybrid-search construction and some security/transaction benefits. Index selection and the main enterprise workload limits remain missing.
- **CC:** **Still nearly empty**: 405-byte report, no AWS or Azure material displayed, no useful comparison, and no manufacturer assertion elevated to objective truth because no assertion survives at all. The missing source qualification causes entire dimensions to disappear.
- **TM:** The model-diversity section is useful. The regional section is narrow, and the enterprise-controls section drifts to generic governance tools. Six attributed evidence notes recover some context but add noise.
- **CR:** Not an empty file, but it shows neither the vendor score nor the independent replication result. It mentions version release dates and vendor evaluation settings, and abstains from declaring either side correct. It does **not** accomplish the requested conflict presentation or conditions-of-comparison analysis.
- **ED:** Describes pgvector and Milvus capabilities/operations from a single article, including unsafe categorical claims. It has **no enterprise selection or migration advice** and no surviving premise-bound AI inference. It remains a technology description, not a decision aid.

The six files are more varied than the frozen before reports, but the priority CC/CR/ED outcomes do not show clear user-level success. LIMITED_EVIDENCE does not become a satisfied RU.

## Batch 1 Effect

Task categories match all six frozen development labels, and FV/TM have visible dimension-specific sections. Substantive demand coverage is inconsistent: TC omits indexes, CC omits every comparison, CR omits both results, and ED omits the recommendation. This batch did not reliably prevent missing requirements or topic drift. CC and ED used deterministic research-plan fallback after duplicate requirement structure; the resulting generic “Research … for Development research” headings exposed a planner alignment failure.

## Batch 2 Effect

Source identity was present in **106/174** selected evidence chunks; publication date in **86/174**. Among **41** distinct evidence IDs used by final factual and limited layers, **27** had a qualified publication date. Those fields helped the TM model-diversity result pass, but implementation presence did not make qualification reliable: all six executions report **zero primary-source qualifications**; FV cites an unowned OpenAI-policy mirror; ED's two cited chunks have unknown source organization and date; TM identifies Computer Weekly and Kiteworks through Facebook URLs. A Speakeasy page has publication metadata `2026-08-13` but visible content says “Last updated: September 2026” without a day; the updated date remained unknown. Publication metadata therefore did not reliably establish cutoff-safe content.

## Batch 3 Retrieval Effect

`NEEDS_RETRIEVAL` before second retrieval: **9** (TC 1, CC 3, CR 4, ED 1). Second-round queries: **8** across those four cases. READY recovery: **1** (TC's R1 hybrid requirement). Still unresolved after the second round: **8**. Additional retrieved candidates: **21** (TC 10, CR 11; CC and ED 0). Recorded additional search latency: **15.486 seconds**. Incremental provider tokens/cost for second retrieval are unavailable. TC's readiness recovery still did not satisfy the hybrid RU's first-party-plus-independent strength rule, while its missing index RU was not retrieved as a gap; CC and ED gained no candidates. Bounded gap search had low demonstrated value in this sample.

## Batch 4 Layered Output Effect

The layered renderer recovered **7 LIMITED_EVIDENCE** notes: six in TM and one vendor-setting quote in CR. They show source-attributed material with caveats, but they did not restore CC's two sides, CR's disputed results or ED's decision. **No AI_INFERENCE survived in any report**; CR recorded one invalid inference with a failed premise and excluded it. The earlier blanket omission was partially relieved in TM, but the key requested utility correction was not achieved. One rejected Gartner-spending claim reappeared verbatim as an attributed evidence note; it is not counted as a satisfied RU or as a verified fact.

## Layered Output Counts

| Case | VERIFIED_FACT | LIMITED_EVIDENCE | AI_INFERENCE | UNRESOLVED |
| --- | ---: | ---: | ---: | ---: |
| FV | 8 | 0 | 0 | 0 |
| TC | 8 | 0 | 0 | 1 |
| CC | 0 | 0 | 0 | 4 |
| TM | 14 | 6 | 0 | 0 |
| CR | 1 | 1 | 0 | 3 |
| ED | 7 | 0 | 0 | 2 |
| **Total** | **38** | **7** | **0** | **10** |

These are runtime output-layer counts, not independent safety or RU judgments.

## Safety

All six final reports were read beside their saved evidence, emitted/omitted Gate records and Grounding records. The findings below are report-level observations. External first-party technical documentation was used only as an explicitly separate safety cross-check, never to add evidence to frozen RU scoring.

| Check | Findings | Concrete report observation |
| --- | ---: | --- |
| Unsupported or false fact presented as VERIFIED | **4 confirmed** | FV calls abuse monitoring/legal retention an exception to no-training, although its cited OpenAI material treats training opt-in and retention as separate policies. The cited OpenAI page **does** support the CSAM manual-review detail; that detail is not counted as an unsupported fact. ED says PostgreSQL lacks multi-core parallel scans, says pgvector lacks binary vectors/quantization, and says Milvus production requires Pulsar or Kafka. Those three categorical ED assertions conflict with [PostgreSQL parallel-query documentation](https://www.postgresql.org/docs/17/parallel-plans.html), [pgvector's project documentation](https://github.com/pgvector/pgvector), and [Milvus's 2025 Woodpecker announcement](https://blog.milvus.io/blog/introduce-milvus-2-6-built-for-scale-designed-to-reduce-costs.md), respectively. ED's seven factual records also rely on only one unknown-owner article, so broader evidence-strength risk remains. |
| Rejected claim restored verbatim in LIMITED | **1** | TM's rejected Gartner `$1 billion by 2030` claim reappears word-for-word in a clearly attributed source quote with a limitation sentence. Attribution prevents it from being an unqualified system assertion, but it is a literal reappearance. |
| AI_INFERENCE fabrication of source-free numbers/dates/benchmarks/rankings/status/company behavior | **0 observed** | There are no surviving AI_INFERENCE records in any of the six reports; the invalid CR inference was excluded. This was checked in the final text, not inferred solely from the counter. |
| Conflict overclaim | **0 observed** | CR makes no unsupported adjudication; its problem is omission of both scores and the actual disagreement. |
| Temporal leakage / unknown update date used for cutoff-current TM facts | **2 cutoff-unverified claims** | Two TM governance-platform factual paragraphs use the Speakeasy page whose text says it was last updated in September 2026 without a verified day, under the report's `2026-09-05` cutoff heading. Actual post-cutoff publication is not established, so this is a cutoff-verification failure, not a proven later-date source. No separate unknown-date source was found asserting “latest” without qualification. |

The internal Grounding records call all 38 emitted records `pass`; that is not sufficient evidence of factual safety. The confirmed ED errors show that source-text support from a single unqualified article can still produce false VERIFIED output.

## Readability

| FV | TC | CC | TM | CR | ED |
| --- | --- | --- | --- | --- | --- |
| ACCEPTABLE | ACCEPTABLE | NOISY | NOISY | NOISY | NOISY |

FV and TC have readable sections but many evidence IDs and mixed Chinese/English prose. CC repeats four identical abstentions; TM repeats evidence-note disclaimers and mixes general governance material into cloud-service analysis; CR repeats abstentions without a comparison; ED repeats abstentions after an unsupported technology list. No report demonstrates a useful, premise-bound AI analysis section.

## Remaining Failure Map

- **Evidence strength and source identity:** FV retention, TC hybrid/limits, TM regional/controls, ED capabilities/operations. ED's single-source categorical facts are also a safety issue.
- **Requirement and generation alignment:** TC indexes; CC's three comparisons; CR's two results and conflict explanation; ED's migration recommendation.
- **Retrieval utility:** CC and ED second searches returned no candidates and no READY recovery; CR gained candidates but no READY recovery or disputed result in the final report.
- **Temporal qualification:** TM's September-updated governance source lacks a verified update day against the frozen cutoff.
- **Layered output utility:** TM source notes help modestly; the priority CC/CR/ED gaps are not safely recovered by limited disclosure or inference.

These are measured post-correction failures. They do not change the frozen case list, rubric, acceptance criteria or V1 baseline.

## Cost and Runtime

| Case | Runtime seconds | Search calls | Second-round queries | Runtime estimated USD |
| --- | ---: | ---: | ---: | ---: |
| FV | 169.960 | 4 | 0 | 0.98936988 |
| TC | 196.811 | 5 | 1 | 0.86898376 |
| CC | 90.253 | 8 | 3 | 0.28453708 |
| TM | 205.879 | 4 | 0 | 0.76197032 |
| CR | 178.992 | 7 | 3 | 0.74537328 |
| ED | 129.413 | 6 | 1 | 0.48668810 |
| **Total** | **976.615 wall seconds** | **34** | **8** | **4.13692242** |

Per-case runtime is task creation-to-update duration; total is first task creation to final task update, including inter-case gaps. ResearchConductor recorded **0 search-call failures**, while individual fetched pages did fail or return empty context. Retrieval calls: **30**. Provider token usage: **unavailable**. Incremental second-round provider cost: **unavailable**. `actual_provider_bill`: **unavailable**, never zero. The estimated cost is the runtime's estimate, not a provider invoice.

## Integrity

No code or tuning changed between cases; no quality-based rerun occurred; the rubric and development/holdout split stayed frozen; prior invalid runs were not appended; runtime source was unchanged; holdout runs, searches, evaluations and tuning stayed at zero. All six reports were inspected instead of accepting internal Gate/Grounding counters as a safety verdict.

## Final Interpretation

1. **Batch 1–4 did not succeed as a complete utility correction.** Classification and some TM model coverage improved, but the planner, qualification, gap search and layered output did not rescue CC/CR/ED.
2. **Strict RU moved from 1/18 to 2/18.** The gain is one independently dated TM model-diversity unit; no partial credit was used.
3. **Final user reports improved unevenly.** FV/TC/TM contain useful material; CC remains almost empty, CR does not show the conflict, and ED offers no decision.
4. **Truthfulness was sacrificed in some VERIFIED output.** Manual inspection found four confirmed factual/semantic errors, a verbatim rejected-claim quote and two cutoff-unverified TM claims. They were not hidden by a favorable internal validation count.
5. **Core work remains worth reviewing before any freeze or holdout:** the false single-source ED assertions, cutoff qualification and missing priority-case utility. This report does not authorize or perform a runtime repair or new paid run.

## Final Recommendation

**No listed recommendation is valid for these observed results.** `FREEZE_V2_AND_PROCEED_TO_FINAL_HOLDOUT_BENCHMARK` fails the completeness, priority-case and safety conditions. `FREEZE_V2_WITH_KNOWN_STRICT_COVERAGE_TRADEOFF` fails its utility and no-safety-regression conditions. `STOP_AND_REVIEW_ONE_DETERMINISTIC_BLOCKER` would falsely describe six successful report generations as blocked by a deterministic code exception. The evidence supports stopping at this decision boundary and reviewing the measured safety and utility failures; **holdout remains untouched**.
