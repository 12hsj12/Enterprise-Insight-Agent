# Enterprise Insight Agent V2 — Frozen Architecture Specification

**Specification:** `enterprise-insight-v2-architecture/2.0.0`

**Status:** FROZEN

**Frozen on:** 2026-09-08
**Implementation baseline:** `d172cb86d184a6f39fb976fbdc3cf8868f1250af` on `feat/evidence-v2`

This document freezes the V2 contracts before feature implementation and before any final
experiment. A later change requires a new specification version, a change note, and a new
dataset hash. It must not mutate V1 history or artifacts.

## 1. What exists at the freeze point

The current implementation is a V1 foundation, not the V2 system described below.

- `Evidence` stores source content and provenance. `EvidenceAssessment` stores a
  source-level reliability prior. `EvidenceConsistencyAssessment` summarizes explicit
  cross-evidence relationships. `ClaimEvidenceLink` represents one claim/evidence
  relationship. These meanings remain separate.
- `EvidenceReliabilityEvaluator` classifies URLs with the shared domain rules and assigns
  authority anchors. `authority_score` is neither truth probability, claim confidence,
  factual correctness, nor consistency.
- `ContextCompressor` applies semantic filtering first and optionally reranks surviving
  documents with `(1-w)*similarity + w*authority`. Only its web-compression path currently
  returns structured `EvidenceContext`; the vector-store path still returns prose context.
- `ContextManager` records selected evidence and source assessments. It does not classify
  the research task or apply a query-aware policy.
- `IntelligenceWorkflow` asks the model to cite and not invent facts, then preserves report
  prose plus evidence. It does not plan claims, bind claims to evidence, gate claims, verify
  cutoff dates, or perform grounding validation. Consistency is currently `insufficient`
  without externally supplied explicit links.
- `EvidenceAssessment.freshness_score` is currently `None`. `RunTrace` records bounded,
  content-free operational events, but has no V2 policy or claim-gate event schema.
- V1 benchmark tooling is fixed to its 12-case V0 dataset and two variants. Its reviewed
  result was mixed: development Citation Correctness rose, holdout Citation Correctness
  fell, Citation Completeness slightly fell, and Required Unit coverage saturated. V2
  therefore cannot claim that source reranking alone improved general research quality.

## 2. Frozen V2 flow and ownership

The required flow is:

`Query -> ResearchTaskClassifier -> EvidencePolicy -> candidate retrieval -> policy reranking
-> evidence context -> claim planning -> claim/evidence binding -> claim gate -> report
generation -> grounding validation`

Ownership remains layered:

| Layer | Owns | Must not own |
|---|---|---|
| Evidence | source payload, provenance, publication observations | claim truth |
| Reliability | shared source classification and authority prior | task policy or claim confidence |
| Context/RAG | semantic filtering, policy reranking, selected evidence | final factual assertions |
| Claim grounding | claim plan, links, risk rules, gate decision | URL classification duplication |
| Enterprise workflow | sequencing and typed result assembly | alternate evidence semantics |
| Evaluation | frozen cases, annotations, metrics, acceptance | tuning holdout after observation |
| Trace | bounded decision metadata and costs | raw content, secrets, private reasoning |

## 3. Task classification contract

`ResearchTaskCategory` is a closed enum:

1. `factual_verification`
2. `technical_capability_analysis`
3. `competitive_comparison`
4. `trend_market_intelligence`
5. `conflict_credibility_resolution`
6. `enterprise_decision_recommendation`

`TaskClassification` is a typed record with:

- `category: ResearchTaskCategory`
- `confidence: float[0,1]` — classifier confidence only, never factual confidence
- `classifier_version: str`
- `matched_signal_codes: list[str]`
- `runner_up_categories: list[ResearchTaskCategory]`
- `rationale_codes: list[str]` — concise public reasons, not chain-of-thought
- `fallback_used: bool`

The initial classifier is deterministic and rule-based. Precedence for overlapping requests
is: explicit decision/recommendation, explicit contradiction/credibility resolution,
multi-entity comparison, time/market trend, narrow fact verification, then technical
analysis. A tie after precedence falls back to `technical_capability_analysis`, records
`fallback_used=true`, and may not silently choose based on benchmark split. The frozen
dataset category is the evaluation label, not an input to production classification.

## 4. EvidencePolicy schema and frozen mapping

`EvidencePolicy` is immutable per classification and includes:

- `policy_version`, `category`, `authority_weight`
- `preferred_source_types` in ranked order
- `freshness_mode`: `not_required | contextual | strict`
- `max_age_days: int | null`
- `corroboration_rule`
- `primary_source_rule`
- `independent_source_rule`
- `reason_codes`

The canonical values live in
`benchmarks/dataset/enterprise_insight_bench_v2.json`. The mapping is frozen as follows:

| Category | w | Freshness | Default evidence rule | Policy reason |
|---|---:|---|---|---|
| factual verification | 0.30 | contextual, 365 d | one appropriate primary or two independent sources | direct records are useful for narrow facts |
| technical/capability | 0.22 | contextual, 730 d | primary technical material plus independent corroboration for high-risk claims | relevance and technical specificity dominate |
| competitive comparison | 0.10 | strict, 365 d | comparable primary evidence for each entity plus one independent synthesis source | symmetric evidence prevents one-sided comparison |
| trend/market intelligence | 0.12 | strict, 180 d | at least two independent sources spanning the claimed trend | diversity and recency outweigh vendor prestige |
| conflict/credibility | 0.18 | contextual, 365 d | evidence for each side plus an independent adjudicating source when available | authority must not erase genuine disagreement |
| enterprise decision/recommendation | 0.08 | contextual, 730 d | evidence for material premises from at least two independent source families | recommendations must expose premise uncertainty |

Semantic relevance remains dominant because every frozen `w <= 0.30`; reranking occurs only
after the semantic eligibility filter. These weights are design anchors, not learned optima,
and must not be swept on holdout. V1 remains the fixed `w=0.20` ablation.

### Authority anchors

V2 reuses the current shared anchors unchanged: `official=1.00`,
`authoritative_media=0.85`, `web=0.60`, `unknown=0.30`. They are coarse source priors chosen
for backward-compatible, interpretable ordering. They do not account for whether a source
supports a particular claim, whether it is current, or whether an official source has a
commercial conflict. Preferred policy source roles such as official documentation,
regulator/standard, peer-reviewed research, independent major media, industry analysis,
and practitioner evidence are provenance roles. Extending their recognition must happen in
the shared reliability layer rather than through a second domain classifier.

Independence is assessed at publisher/organization ownership level, not URL count. Mirrors,
syndications, press-release republications, and multiple pages from one organization count
as one source. Primary evidence is required only when the rule says so; otherwise it is a
preference and cannot compensate for low relevance.

## 5. High-risk claims, binding, and gate

The closed high-risk taxonomy is:

- `numeric_value`
- `date_or_time_window`
- `release_status_availability`
- `comparative_claim`
- `superlative_or_ranking`
- `market_metric`
- `benchmark_or_performance`
- `conflict_sensitive_claim`

Each planned factual claim has a stable `claim_id`, normalized text, risk types, materiality,
and explicit `ClaimEvidenceLink` objects. A valid supporting link requires passage-level
support and matching scope/time/entity; URL presence alone is insufficient.

Frozen evidence-strength rules are:

- `standard`: at least one valid supporting source.
- `primary_or_two_independent`: one appropriate primary source, or two independent
  supporting sources.
- `primary_plus_independent`: one appropriate primary source and one independent source.
- `two_independent`: two independent supporting organizations.
- `conflict_sides_plus_adjudicator`: support for every material side and one independent
  adjudicator; when no adjudicator exists, the claim may only be emitted as unresolved.

The high-risk type selects this minimum rule before a stricter case/Required Unit rule is
applied:

| High-risk type | Frozen minimum rule |
|---|---|
| `numeric_value` | `primary_or_two_independent` |
| `date_or_time_window` | `primary_or_two_independent` |
| `release_status_availability` | `primary_or_two_independent` |
| `comparative_claim` | `two_independent`; direct product comparisons additionally require comparable primary evidence for each entity |
| `superlative_or_ranking` | `two_independent` |
| `market_metric` | `primary_or_two_independent` |
| `benchmark_or_performance` | `primary_plus_independent` |
| `conflict_sensitive_claim` | `conflict_sides_plus_adjudicator` |

When several types apply, the gate enforces the union of their requirements; it never picks
the easiest alternative. The case or Required Unit rule may strengthen but never weaken this
minimum.

Gate decisions are `emit`, `hedge`, `omit`, or `retrieve_more`. `emit` requires the case/unit
rule and every applicable high-risk rule. `retrieve_more` is allowed only inside the bounded
workflow and budget. If it remains insufficient, the deterministic fallback is `hedge` for
useful qualified uncertainty or `omit` for an unsupported assertion. Conflicting evidence
may not be averaged into confidence. The gate records rule codes, supporting/conflicting
evidence IDs, independence groups, and a concise reason.

Grounding validation runs after report generation. It resegments factual claims, verifies
that emitted claims preserve the approved meaning and citations, re-applies the gate rules,
checks post-cutoff evidence, and returns `pass`, `repair_required`, or `fail`. At most one
local report repair pass is allowed within a run; it may remove/hedge claims or correct links,
but may not fabricate evidence. Any remaining gate violation makes the run fail evaluation.

## 6. Explainability and compatibility

V2 diagnostics must expose classification, policy version and values, semantic/authority/
final ranking components, freshness decisions, evidence rejection codes, planned claim risk,
link IDs, gate decisions, grounding results, scoped latency/token/search/cost counters, and
failure classes. They must not expose raw evidence content, credentials, signed URLs, or
private reasoning. Existing callers with V2 disabled retain the V1-compatible behavior.

## 7. Frozen specification register (28 items)

Every item below is frozen by this document, the benchmark specification, or the dataset:

1. six-category taxonomy;
2. classifier schema;
3. deterministic classifier precedence/fallback;
4. EvidencePolicy schema;
5. category-to-policy mapping;
6. authority weights;
7. authority-anchor rationale and semantics;
8. preferred source roles;
9. freshness modes and windows;
10. corroboration rules;
11. independence definition;
12. primary-source rules;
13. high-risk claim taxonomy;
14. evidence-strength rules;
15. claim/evidence binding contract;
16. claim-gate decisions and fallback;
17. grounding-validation contract;
18. 30-case case list;
19. 18/12 stratified dev/holdout split;
20. information cutoff;
21. per-case Required Units and rules;
22. Citation metrics;
23. Strong Evidence Coverage;
24. Source Reliability Score;
25. High-Risk Claim Corroboration Rate;
26. classification/category/generalization metrics;
27. annotation and paired-fixture protocol;
28. Baseline/V1/V2 variants, cost controls, and quantitative fail-capable acceptance.

Implementation or measurement is not implied by this freeze. V2 completion still requires
code, independent review, real recorded tests, and—if provider access and user-authorized
budget permit—a non-cherry-picked final experiment.
