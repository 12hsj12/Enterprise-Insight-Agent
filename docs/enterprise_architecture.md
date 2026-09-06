# Enterprise Insight Agent v1 architecture

The business problem is making competitive-intelligence findings inspectable: an analyst
needs the source behind a finding, the reason a source was preferred, and the limitations
of the resulting report. GPT Researcher's planning, search, scraping, compression and
writing already provide the research execution path. This project extends that path.

## Data flow

```text
Typed request -> IntelligenceWorkflow -> GPTResearcher planning/search/scraping
                                             |
                                             v
                        ContextManager -> ContextCompressor
                                             |
                     chunking -> semantic filter -> optional source reranking
                                             |
                              EvidenceContext: text + Evidence + diagnostics
                                 /                         \
                                v                           v
                       report generation        source reliability assessments
                                \                           /
                                 v                         v
                          IntelligenceResult (report + provenance)
                                      |
                        consistency: insufficient without reviewed links
                                      |
                    FastAPI TaskRecord -> SQLite history / restart recovery

RunTrace observes research, writing, web search and retrieval selection.
Benchmark runner -> raw artifacts -> reviewed annotations -> metrics/comparison.
Explicit ClaimEvidenceLink inputs -> existing consistency evaluator (library API).
```

The diagram describes the implemented web compression path. Vector-store and MCP context
paths still exist upstream and do not yet provide the same structured evidence coverage.

## Contracts

| Model | Responsibility | Deliberately not inferred |
|---|---|---|
| `Evidence` | Source content, URL, title, subquery and stable content-derived ID | Claim confidence or factual correctness |
| `EvidenceAssessment` | Source reliability prior using existing domain rules | Truth probability; freshness currently null |
| `EvidenceConsistencyAssessment` | Aggregate relations from explicit links | Automated fact verification |
| `ClaimEvidenceLink` | A claim's support/conflict/unclear relationship to evidence | Links derived merely from shared URLs |
| `RetrievalDiagnostic` | Similarity, authority prior, combined score, evidence ID | Report-quality judgment |

`ContextManager` records evidence and its assessment after web compression. The workflow
deduplicates identical evidence IDs, rejects conflicting objects with the same ID, and
requires matching evidence/assessment ID sets. It keeps the generated report as prose;
it does not pretend that its Markdown sections are a validated extracted knowledge graph.

## Ranking and compatibility

`final_score = (1 - w) * similarity_score + w * authority_score`

`SOURCE_RELIABILITY_WEIGHT` travels through normal `Config` defaults, JSON files and
environment overrides. Default `w=0` preserves ordering and the short-document fast path.
Explicit legacy compressor kwargs remain supported. Positive weight reranks after the
existing chunker and semantic filter; it never promotes an irrelevant document that failed
the filter. The candidate `w=0.2` was not optimized. The authority classifier is shared
with evidence assessment, rather than copied into the business workflow.

This is a source-prior reranker, not a neural reranker. Domain lists are curated and
incomplete; official company sources can be biased. Similarity and authority combine
heuristically, and the current API permits weights that can make authority dominate.
Use conservative settings and evaluate the actual task distribution.

## Observability and persistence

Optional `RunTrace` uses `ContextVar` for isolation across concurrent async tasks and a
bounded event buffer. It records stage durations, failure classes, scoped search counts,
selected evidence counts, ranking scores and relevant settings. It avoids query text,
document content and source URLs. Benchmark artifacts contain raw research material in
ignored local output directories and therefore have a different privacy boundary.

The enterprise API uses SQLite through the existing async report-store operation shape.
Connections run in worker threads; parameterized SQL and transactions preserve independent
writes. Existing UI JSON reports remain separate. Malformed JSON stores raise rather than
being treated as empty and overwritten. No new persistence package is required.

One server worker is the supported deployment. On startup, stored `running` tasks become
`interrupted`; completed history survives. Requests execute synchronously and have a
deadline. Cancellation is best effort for blocking worker-thread/provider operations.
There is no durable queue, distributed lease, automatic task replay or application-level
retry that could duplicate paid research. Existing provider retries remain in force.

## Evaluation boundaries

The frozen 12-case benchmark has 8 development and 4 holdout cases with cutoff 2026-09-05.
The current comparison is a same-version zero-weight ablation, separate from the original
historical upstream baseline. Configurations, commit SHA, dataset/report hashes, runtime
versions, failures and raw outputs make runs inspectable. Live web and model responses
remain nondeterministic; concurrent local work prevents controlled latency conclusions.

Quality scoring requires reviewed fact/claim/citation counts tied to an exact report hash.
The scorer validates counts and applies the documented formulas; it does not replace the
reviewer. Missing annotations remain null. Source authority and cross-source consistency
cannot substitute for checking whether each cited passage supports its associated claim.
