# Six-case development calibration review package

**READY_FOR_HUMAN_REVIEW. Human review: PENDING. Reviewer: null.**

Six fixed development cases ran once through the production enterprise POST router,
IntelligenceWorkflow, GPTResearcher, ResearchConductor, search/scrape, ContextManager
and V2 Claim/Gate/Grounding path with `enable_v2_execution=true`. ASGI transport was
in-process; provider, search, scraping and embedding execution was real.

Start with [HUMAN_REVIEW_QUEUE.md](HUMAN_REVIEW_QUEUE.md). The package now has
three explicit layers: [FULL_AI_ASSISTED_LEDGER.json](FULL_AI_ASSISTED_LEDGER.json)
preserves all 483 pre-annotation objects; [HUMAN_CALIBRATION_CORE.json](HUMAN_CALIBRATION_CORE.json)
contains 51 bounded calibration tasks; and [HUMAN_ADJUDICATION_QUEUE.json](HUMAN_ADJUDICATION_QUEUE.json)
contains 36 genuine semantic/adjudication tasks. [HUMAN_REVIEW_QUEUE.json](HUMAN_REVIEW_QUEUE.json)
is the combined 87-task entry point. None is final gold and every human field remains unset.

The 483-object ledger still contains 115 proposed atomic factual claims, 3
non-factual segments, 184 citation pairs, 18 Required Units, 45 source-strength
items, 45 independence items, 45 freshness items and 28 high-risk items. The
compression changes triage only. It does not change any recommendation or label.
Related claim segmentation, citation-support and high-risk ledger records are
grouped at a shared parent-report boundary so the reviewer makes one coherent
semantic decision without losing any item-level audit reference.

Each case directory contains report.md, selected.json, scoring.json, execution.json,
trace.json, diagnostics.json, citation_mapping.json, review_sheet.json,
case_input.json, artifact_references.json, scoring_input.json and hashes.json.
The report preserves actual final bytes. Curated execution/trace JSON copies use
LF line endings; original Windows runtime bytes remain untouched with separate
references and hashes, and decoded objects are verified equal. Competitive
comparison and conflict resolution emitted no claims; each has three proposed
unsatisfied Required Units, rather than fabricated report content or failed-run labels.

Candidate page and eligible-chunk material is distinct from selected evidence.
Candidate/task JSON remains in ignored `outputs/calibration-six-20260911/` and is
referenced with hashes. A repository checkout alone does not include those local
files. A complete local transfer archive is provided at
`outputs/calibration-six-20260911-review-package.zip`; extract its repository-relative
paths together to resolve the local candidate references. Original absolute runtime
paths are provenance, while `artifacts.path` values are the resolving references.
The archive is ignored and must be transferred separately; its external SHA-256
receipt is `outputs/calibration-six-20260911-review-package.sha256`.

Review only saved material. Do not browse to silently supplement facts, promote
runtime Gate verdicts to gold, or use source authority as a truth/primary-source
proxy. Short segments inherit their exact parent sentence and qualifiers, including
negation and unconfirmed prefixes via output_mode. Revisit ambiguous segmentation
before support scoring. Each atomic citation gets support/conflict/unclear treatment
without partial credit. Required Units require full coverage and frozen strength.
Different domains and repeated chunks do not establish independent publishers.

Dates are proposed from exact saved excerpts. Unknown dates fail strict freshness;
contextual modes retain explicit flags. Competitive comparison selected a NextGen
article dated 2026-09-08, after cutoff; it is excluded from scoring and retained for
audit. The CSDN recommendation timestamp in the decision case is potentially late
but ambiguously attributed and remains unverified. These observations are not fixed
by changing the frozen runtime. Numeric source-table values do not count as report
risk coverage when omitted from the report.

Covered report risks: numeric_value, release_status_availability, comparative_claim,
benchmark_or_performance, conflict_sensitive_claim. Coverage gaps:
date_or_time_window, market_metric, superlative_or_ranking. No additional cases were
substituted or added.

The runtime accumulated USD 3.68123008 in estimates across the six calls. Actual
provider billing and token totals are unavailable; the inherited estimate uses
generic pricing and may include an embedding estimate despite local HuggingFace
execution. Do not describe it as an invoice. Official benchmark cost: USD 0.

See [SIX_CASE_DELIVERY.md](SIX_CASE_DELIVERY.md),
[CALIBRATION_MANIFEST.json](CALIBRATION_MANIFEST.json), and
[CAPTURE_IMPLEMENTATION_REVIEW.md](CAPTURE_IMPLEMENTATION_REVIEW.md).
Frozen dataset SHA, cutoff, rubric and Agent semantics are unchanged. No holdout
report was executed, opened for evaluation, annotated or used for tuning.

Human reviewer reviews the compressed calibration core and adjudication queue.
