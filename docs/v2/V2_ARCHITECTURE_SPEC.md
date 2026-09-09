# Enterprise Insight Agent V2.1 — Frozen Architecture Specification

**Specification:** `enterprise-insight-v2-architecture/2.1.0`

**Policy resolver contract:** `enterprise-insight-policy-resolver/1.0.0`

**Status:** FROZEN

**Frozen on:** 2026-09-09
**Revision baseline:** `b0caaed358dbb2d5f3972041c73586055b30d2d7` on `feat/evidence-v2`

This document re-freezes the V2 target architecture after the approved Architecture
Decision Review. It supersedes the 2.0 specification without rewriting the historical
2.0 freeze commit. The revision changes routing and safety ownership only: the taxonomy,
benchmark content, EvidencePolicy values, high-risk rules, metrics, thresholds, and V1
history remain unchanged.

This is a specification checkpoint. At this freeze point, Batch 2 still implements
single-policy selection from the primary classifier result. `PolicyResolver`, multi-policy
fusion, claim gating, and grounding validation described below are target behavior for
later implementation and are not claimed to exist in production code.

## 1. Existing implementation boundary

- `Evidence` stores source content and provenance. `EvidenceAssessment` stores a source-level
  reliability prior. `EvidenceConsistencyAssessment` summarizes explicit cross-evidence
  relationships. `ClaimEvidenceLink` represents one claim/evidence relationship. These
  meanings remain separate.
- `EvidenceReliabilityEvaluator` classifies URLs with shared domain rules and assigns
  authority anchors. `authority_score` is neither truth probability, claim confidence,
  factual correctness, nor consistency.
- `ContextCompressor` performs semantic filtering and can rerank the survivors with one
  configured authority weight. It does not yet resolve or fuse several policy branches.
- `ContextManager` currently passes one selected EvidencePolicy to compression. Its current
  structured metadata cannot honestly establish freshness, source-role, publisher
  independence, primary-source sufficiency, comparison symmetry, or conflict-side coverage.
- `IntelligenceWorkflow` currently classifies a request and resolves the primary category
  directly to one policy when V2 evidence selection is enabled. It does not yet implement
  `PolicyResolver`, claim planning, claim/evidence binding, claim gating, verified cutoff
  enforcement, or grounding validation.
- V1 evidence behavior and V1 benchmark artifacts remain immutable. V1 results were mixed
  and do not establish that source reranking alone universally improves research quality.

## 2. Frozen V2.1 runtime flow and ownership

The required flow is:

```text
Query
-> ResearchTaskClassifier
-> TaskClassification
-> PolicyResolver
-> PolicyRoutingDecision
-> one shared semantic candidate pool
-> branch-local EvidencePolicy reranking
-> deterministic policy-rank fusion
-> EvidenceContext + unresolved policy obligations
-> claim planning
-> claim-risk detection
-> claim/evidence binding
-> classifier-independent Claim Gate
-> report generation
-> grounding validation
```

Semantic retrieval and candidate eligibility occur once per request. Multi-policy routing
must not trigger multiple live searches. Authority or another policy preference cannot
rescue semantically ineligible evidence. A classification error may affect retrieval
preference, but it cannot weaken claim-level minimum evidence rules.

Ownership remains layered:

| Layer | Owns | Must not own |
|---|---|---|
| Evidence | source payload, provenance, publication observations | claim truth |
| Reliability | shared source classification and authority prior | task routing or claim confidence |
| Task classifier | primary category and query-only signals | claim emission or sole policy authority |
| Policy resolver | bounded candidate policies, routing reasons, named obligations | factual correctness or private reasoning |
| Context/RAG | semantic eligibility, branch-local reranking, deterministic fusion | final factual assertions |
| Claim grounding | claim plan, risk detection, links, minimum rules, gate decision | URL classification duplication |
| Enterprise workflow | sequencing, budgets, typed result assembly | alternate evidence semantics |
| Evaluation | frozen cases, annotations, metrics, acceptance | holdout-driven tuning |
| Trace | bounded public diagnostics and costs | raw content, secrets, private reasoning |

## 3. ResearchTaskClassifier contract and reduced responsibility

`ResearchTaskCategory` remains the same closed enum, in this declaration order:

1. `factual_verification`
2. `technical_capability_analysis`
3. `competitive_comparison`
4. `trend_market_intelligence`
5. `conflict_credibility_resolution`
6. `enterprise_decision_recommendation`

`TaskClassification` remains a typed record with:

- `category: ResearchTaskCategory` — one primary category;
- `confidence: float[0,1]` — heuristic classifier confidence only;
- `classifier_version: str`;
- `matched_signal_codes: list[str]`;
- `runner_up_categories: list[ResearchTaskCategory]`;
- `rationale_codes: list[str]` — public reason codes, not chain-of-thought;
- `fallback_used: bool`.

The classifier remains deterministic, query-only, explainable, and a retrieval-preference
input. Its frozen precedence remains: explicit decision/recommendation, explicit
contradiction/credibility resolution, multi-entity comparison, time/market trend, narrow
fact verification, then technical analysis. If no explicit signal resolves the request,
the classifier preserves `technical_capability_analysis` as its primary fallback and sets
`fallback_used=true`. Existing deterministic runner-up ordering is preserved.

Task Classification Accuracy remains measured only on the primary predicted category:

`primary predicted category == frozen category`

Candidate-set membership does not redefine Task Classification Accuracy.

The classifier is no longer architecturally responsible for:

- being the sole EvidencePolicy authority;
- authorizing factual claim emission;
- determining high-risk claim minimum evidence;
- discarding evidence required by a materially plausible alternative task interpretation.

Confidence alone never defines routing clarity because it is heuristic and uncalibrated.

## 4. Frozen PolicyResolver contract

`PolicyResolver` is a deterministic, typed boundary with its own independent version:

`enterprise-insight-policy-resolver/1.0.0`

`resolver_version` must not reuse `classifier_version`. The closed `RoutingMode` values are
exactly:

- `single`
- `multi_policy`
- `broad_fallback`

`PolicyRoutingDecision` is a typed record containing at least:

- `resolver_version: str`;
- `mode: RoutingMode`;
- `primary_category: ResearchTaskCategory | null`;
- `candidate_categories: tuple[ResearchTaskCategory, ...]`;
- `ambiguity_codes: tuple[PublicCode, ...]`;
- `reason_codes: tuple[PublicCode, ...]`;
- `classifier_fallback_used: bool`.

Candidate categories are typed enum values, unique, and deterministically ordered. They
always contain the valid primary category. Only failure to produce a valid typed
classification permits `primary_category=null`; that case still uses broad fallback with
the technical branch first. Public reason and ambiguity codes expose structured decisions
without storing private chain-of-thought.

### 4.1 Routing-mode rules

`single` applies only when all of the following hold:

- the classification is a valid typed result;
- `fallback_used=false`;
- there is no material overlapping runner-up category.

`multi_policy` applies when deterministic classifier output exposes materially plausible
overlapping categories. The candidate set is frozen at a maximum of three policy branches:
the primary category followed by at most the first two material runner-ups in the existing
deterministic classifier order. The bound is a design decision, not a holdout-tuned value.

`broad_fallback` applies when `fallback_used=true` or classification fails to produce a
valid typed result. No LLM classifier is invoked solely to recover routing. For a normal
classifier fallback, `technical_capability_analysis` remains the primary diagnostic
category. The routing candidate set becomes all six policies in this exact order:

1. `technical_capability_analysis`
2. `factual_verification`
3. `competitive_comparison`
4. `trend_market_intelligence`
5. `conflict_credibility_resolution`
6. `enterprise_decision_recommendation`

This is the technical fallback branch first for compatibility, then the remaining five in
the frozen enum declaration order. Broad fallback must be explicitly observable.

## 5. Shared semantic candidate pool

There is exactly one research/search candidate pool per case or request:

`semantic retrieval -> semantic eligibility -> immutable eligible candidate pool`

Every selected policy branch operates on that same pool. Multi-policy routing must not
multiply Tavily searches, live web retrieval, scraping calls, or equivalent provider work.
The paired-candidate-fixture benchmark principle is compatible with and stricter than this
runtime rule. Semantic eligibility precedes all policy reranking; no authority score,
preferred role, freshness preference, or other policy property can admit an ineligible
candidate.

## 6. EvidencePolicy mapping and branch-local reranking

The immutable EvidencePolicy schema remains unchanged from 2.0 and includes:

- `policy_version`, `category`, and `authority_weight`;
- ranked `preferred_source_types`;
- `freshness_mode: not_required | contextual | strict`;
- `max_age_days: int | null`;
- `corroboration_rule`, `primary_source_rule`, and `independent_source_rule`;
- public `reason_codes`.

All category mappings and exact values remain unchanged. The canonical values are in
`benchmarks/dataset/enterprise_insight_bench_v2.json`. Each selected candidate category
resolves independently to its frozen EvidencePolicy:

| Category | w | Freshness | Default evidence rule |
|---|---:|---|---|
| factual verification | 0.30 | contextual, 365 d | one appropriate primary or two independent sources |
| technical/capability | 0.22 | contextual, 730 d | primary technical material plus independent corroboration for high-risk claims |
| competitive comparison | 0.10 | strict, 365 d | comparable primary evidence for each entity plus one independent synthesis source |
| trend/market intelligence | 0.12 | strict, 180 d | at least two independent sources spanning the claimed trend |
| conflict/credibility | 0.18 | contextual, 365 d | evidence for each side plus an independent adjudicating source when available |
| enterprise decision/recommendation | 0.08 | contextual, 730 d | evidence for material premises from at least two independent source families |

For every branch independently:

```text
final_score = (1 - policy.authority_weight) * semantic_similarity
              + policy.authority_weight * authority_score
```

The resolver must not average weights, choose the maximum weight, or invent a merged scalar
policy. Every frozen weight remains at or below 0.30, so relevance stays dominant among
semantically eligible candidates. `authority_score` remains a source-level reliability
prior, never claim truth or primary-source sufficiency.

The shared authority anchors also remain unchanged: `official=1.00`,
`authoritative_media=0.85`, `web=0.60`, and `unknown=0.30`. They are coarse, interpretable
source priors. They do not establish whether a source supports a claim, whether it is
current, or whether an official source has a commercial conflict. The policy weights are
design anchors, not learned optima, and must not be swept on holdout. V1 remains the fixed
`w=0.20` ablation.

Freshness and source-role behavior remains branch-local when structured metadata supports
it. If the required metadata is absent, the system must not fabricate satisfaction; it
retains the requirement as an unresolved named obligation for downstream grounding.

Independence remains publisher/organization ownership-level independence, not URL count.
Mirrors, syndications, press-release republications, and multiple pages from one organization
count as one source.

## 7. Deterministic policy-rank fusion

The frozen fusion algorithm is quota-free deterministic round-robin interleaving:

1. Every selected policy produces a ranked view of the same immutable eligible pool.
2. Branch order is the primary category first, then candidate categories in deterministic
   resolver order. Broad fallback uses the exact order frozen in section 4.1.
3. Visit branches in round-robin order and take the next highest unused evidence from each.
4. Deduplicate by `evidence_id`.
5. Continue until `max_results` is reached or all branch views are exhausted.
6. Stable ties within a branch preserve the existing semantic/source-aware stable order;
   `evidence_id` is the final deterministic tie-break when required.

No tuned numeric rank-fusion hyperparameter is introduced. When `max_results` is less than
the branch count, every branch is not guaranteed representation. The implementation must
record that limitation diagnostically; it must not silently increase search volume.

## 8. Named policy obligations

Policy requirements do not collapse into a scalar. Each applicable policy contributes
named obligations, including where applicable:

- freshness requirement;
- preferred source roles;
- corroboration rule;
- primary-source rule;
- publisher-organization independence rule;
- comparison symmetry;
- conflict-side preservation and adjudication.

`PolicyResolver` preserves the union of these names and their category provenance. Evidence
selection may satisfy some obligations, but unresolved obligations remain explicit in the
EvidenceContext/grounding handoff. The system must not equate several URLs with independence,
declare freshness without publication evidence, infer primary-source sufficiency from
`authority_score`, or infer conflict-side coverage merely from source plurality.

Policy Obligation Preservation is a deterministic contract check: resolver and fusion output
must retain every named obligation contributed by every applicable candidate policy unless
the output records that obligation as satisfied with auditable evidence. Silent loss fails
the contract.

## 9. Classifier-independent Claim Gate minimums

High-risk claim rules are classifier-independent minimums. For every planned factual claim:

`claim risk types -> frozen minimum evidence-strength rules`

No `ResearchTaskCategory`, routing mode, or `EvidencePolicy` may weaken those minima. A wrong
classifier category must never convert a high-risk claim into a standard claim.

The unchanged closed high-risk taxonomy and minimum mapping are:

| High-risk type | Frozen minimum rule |
|---|---|
| `numeric_value` | `primary_or_two_independent` |
| `date_or_time_window` | `primary_or_two_independent` |
| `release_status_availability` | `primary_or_two_independent` |
| `comparative_claim` | `two_independent`, plus comparable primary evidence per entity where applicable |
| `superlative_or_ranking` | `two_independent` |
| `market_metric` | `primary_or_two_independent` |
| `benchmark_or_performance` | `primary_plus_independent` |
| `conflict_sensitive_claim` | `conflict_sides_plus_adjudicator`, or explicitly unresolved wording |

The unchanged strength rules are `standard`, `primary_or_two_independent`,
`primary_plus_independent`, `two_independent`, and
`conflict_sides_plus_adjudicator`. If several risk types apply, the gate combines them with
`union_without_weakening`. A stricter policy obligation or Required Unit rule may strengthen
but never weaken the minimum.

Each factual claim retains a stable `claim_id`, normalized text, detected risk types,
materiality, and explicit `ClaimEvidenceLink` records. A valid support link requires
passage-level support with matching scope, time, and entity; URL presence alone is
insufficient.

Gate decisions remain `emit`, `hedge`, `omit`, or `retrieve_more`. `emit` requires all
applicable claim, Required Unit, and policy obligations. Conflict is never averaged into a
confidence score. Grounding validation resegments generated factual claims, verifies their
meaning and citations, re-applies the classifier-independent gate and cutoff, and returns
`pass`, `repair_required`, or `fail`. At most one local repair pass is allowed; remaining
violations fail evaluation.

## 10. `retrieve_more` semantics and cutoff

Claim-level `retrieve_more` is driven by unmet named claim or policy obligations, not merely
by rerunning the primary category EvidencePolicy. Retrieval remains bounded by workflow,
search, provider, and cost budgets. If required evidence cannot be obtained, the system must
hedge or omit the claim; it must not fabricate satisfaction.

The global information cutoff is unconditional across every routing mode, policy branch,
retrieval attempt, claim decision, and grounding pass.

## 11. Explainability and diagnostics

V2.1 diagnostics must expose primary classification, classifier version/confidence,
matched signals, runner-ups, fallback status, resolver version, routing mode, candidate
categories, ambiguity/reason codes, branch-local policies and scores, fusion order,
obligation status, claim risk, link IDs, gate decisions, grounding results, and scoped
latency/token/search/cost counters. They must not expose raw evidence content, credentials,
signed URLs, or private reasoning.

Routing diagnostics are non-headline and include Policy Candidate Recall, ambiguity rate,
broad-fallback rate, mean and maximum resolved policy count, routing mode by frozen and
predicted category, Policy Obligation Preservation, optional branch evidence overlap, and
local policy-fusion latency. They do not create a synthetic overall score and cannot replace
the existing headline metrics.

## 12. Compatibility, limits, and implementation boundary

- Existing callers with V2 disabled retain V1-compatible behavior.
- The resolver is deterministic and does not call an LLM solely to recover routing.
- A shared pool prevents policy ambiguity from multiplying live search, but it may not
  contain evidence needed by every plausible interpretation.
- Round-robin fusion improves bounded branch exposure but does not guarantee representation
  when `max_results` is smaller than the branch count.
- Routing improves retrieval robustness; the classifier-independent Claim Gate remains the
  safety boundary for factual emission.
- Implementation and measurement are not implied by this freeze. PolicyResolver runtime
  code, Batch 2R, Batch 3, and final benchmark execution remain future checkpoints.

## 13. Frozen specification register

V2.1 freezes:

1. the unchanged six-category taxonomy;
2. the unchanged classifier schema, precedence, fallback, and primary-category metric;
3. PolicyResolver version and typed `PolicyRoutingDecision` contract;
4. exact routing modes and deterministic mode conditions;
5. the three-branch multi-policy bound;
6. broad-fallback triggers and exact six-policy order;
7. one shared immutable semantic candidate pool per request;
8. branch-local use of unchanged EvidencePolicy values;
9. deterministic round-robin fusion and evidence-ID deduplication;
10. named policy-obligation preservation;
11. classifier-independent claim-risk minimums;
12. obligation-driven bounded `retrieve_more` and unconditional cutoff;
13. unchanged high-risk taxonomy, evidence-strength rules, and claim-gate actions;
14. unchanged 30 cases, 18/12 split, Required Units, quality metrics, and acceptance criteria;
15. unchanged Baseline and V1 variants and revised V2 variant;
16. non-headline routing diagnostics and their contracts.

A later semantic change requires a new version, change note, and dataset hash. The current
dataset hash is recorded outside the dataset in the V2.1 change note and benchmark protocol
to avoid self-referential hashing.
