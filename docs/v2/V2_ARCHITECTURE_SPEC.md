# Enterprise Insight Agent V2.2 — Frozen Architecture Specification

**Specification:** `enterprise-insight-v2-architecture/2.2.0`

**Status:** FROZEN

**Frozen on:** 2026-09-09
**Revision baseline:** `d8f210d18059f3dba20d48e6960d6a204d7bd530` on `feat/evidence-v2`

This specification supersedes the active V2.1 target without rewriting its historical
commit or change note. V2.1 proposed uncertainty-aware multi-policy routing. Architecture
review found that proposal disproportionate to the original Query-aware Evidence Selection
goal. V2.2 limits task classification to choosing one adaptive authority weight.

The six-category taxonomy, benchmark cases, split, cutoff, Required Units, EvidencePolicy
anchors, high-risk rules, metrics, thresholds, and frozen V1 evidence remain unchanged.

## 1. Architecture boundary

- `Evidence` owns source content and provenance.
- `EvidenceAssessment` owns an individual source-level reliability prior.
- `EvidenceConsistencyAssessment` owns explicit consistency relationships across evidence.
- `ClaimEvidenceLink` owns an explicit claim/evidence relationship.
- `authority_score` is a source-level reliability prior. It is not truth probability,
  factual correctness, claim confidence, consistency, or permission to emit a claim.
- `EvidenceReliabilityEvaluator` and the existing shared domain/source classification rules
  remain the authority-prior implementation.

## 2. Frozen Batch 2 runtime flow

```text
Query
-> ResearchTaskClassifier
-> primary ResearchTaskCategory
-> adaptive authority_weight
-> semantic candidate eligibility
-> SourceAwareScorer
-> EvidenceContext
```

Task classification causes no extra retrieval. There is one semantic selection path and one
source-aware reranking pass. No category branch other than the primary category executes.

The mandatory ordering is:

```text
semantic retrieval -> semantic eligibility/filtering -> adaptive source-aware reranking
```

An authority prior cannot rescue semantically ineligible evidence. The weighted standard
path fails safely when an eligible document lacks `query_similarity_score`.

## 3. ResearchTaskClassifier responsibility

`ResearchTaskCategory` remains the closed enum, in this declaration order:

1. `factual_verification`
2. `technical_capability_analysis`
3. `competitive_comparison`
4. `trend_market_intelligence`
5. `conflict_credibility_resolution`
6. `enterprise_decision_recommendation`

`TaskClassification` retains:

- one primary `category`;
- heuristic `confidence` in `[0,1]`;
- `runner_up_categories`;
- matched signal codes and rationale codes;
- `fallback_used`;
- classifier version.

The classifier remains deterministic, query-only, and explainable. Its confidence is not a
calibrated probability. Runner-ups and confidence are diagnostics only: neither changes the
runtime weight or causes another selection path. Only the primary category chooses the
normal adaptive weight.

If no explicit signal resolves the request, the diagnostic primary category may remain
`technical_capability_analysis` for compatibility and `fallback_used=true`. Long-tail
natural-language misclassification is an accepted limitation of this soft-ranking feature;
the classifier is not required to be linguistically complete.

Task Classification Accuracy remains exactly:

`primary predicted category == frozen category`

## 4. Adaptive authority-weight contract

For a successful usable primary classification:

| Primary category | authority_weight |
|---|---:|
| `factual_verification` | 0.30 |
| `technical_capability_analysis` | 0.22 |
| `competitive_comparison` | 0.10 |
| `trend_market_intelligence` | 0.12 |
| `conflict_credibility_resolution` | 0.18 |
| `enterprise_decision_recommendation` | 0.08 |

These unchanged values are interpretable design anchors, not learned optima. They must not
be swept or tuned on holdout.

When `fallback_used=true`, or a classification is missing or cannot provide a valid usable
category, the effective runtime weight is the neutral V1 source-aware value:

`authority_weight = 0.20`

The compatibility diagnostic category does not change this fallback. Fallback status, the
policy anchor, and the effective weight are recorded separately in diagnostics.

For semantically eligible evidence, `SourceAwareScorer` preserves:

```text
final_score = (1 - w) * semantic_similarity + w * authority_score
```

Every adaptive weight is at most 0.30, so semantic relevance remains the dominant component.
`w=0` preserves semantic-only behavior. V1 fixed `w=0.20` remains available independently
of V2 classification.

## 5. EvidencePolicy scope

The typed immutable `EvidencePolicy` model and all six frozen policy records remain. In
Batch 2, only `authority_weight` is actively enforced by retrieval ranking.

The remaining fields—preferred source types, freshness, corroboration, primary-source
rules, and independence—are explicit metadata and downstream guidance. A predicted category
does not turn them into hard safety rules. The current evidence model lacks enough structured
publication, ownership, and source-role data to claim that these rules are enforced, so
their limitations stay observable rather than fabricated.

## 6. Claim-safety ownership

`ResearchTaskClassifier` does not authorize factual claim emission. Task category does not
determine or weaken minimum claim support. High-risk claim rules are classifier-independent
and combine without weakening.

The future post-Batch-2 flow remains:

```text
EvidenceContext
-> Claim Model
-> Claim Risk Types
-> Claim/Evidence Binding
-> Claim Gate
-> Grounding Validator
```

Those later layers are not implemented by Batch 2. Their frozen minimums remain:

| Claim risk | Minimum evidence rule |
|---|---|
| `benchmark_or_performance` | `primary_plus_independent` |
| `comparative_claim` | `two_independent`, plus comparable primary evidence where required |
| `conflict_sensitive_claim` | `conflict_sides_plus_adjudicator` |
| numeric/date/release/market metric | `primary_or_two_independent` |

Required Unit and multi-risk rules remain `union_without_weakening`. Classifier correctness
cannot weaken these rules.

## 7. Variants and ablation

- Baseline: semantic-only evidence selection, `w=0`, no task-aware preference, no claim gate.
- V1: fixed source-aware reranking, `w=0.20`, no task-aware preference, no claim gate.
- V2: deterministic task classification, adaptive authority-weight source-aware reranking,
  evidence-gated claim generation, and grounding validation.

The retrieval ablation is therefore clear:

```text
Baseline -> no authority prior
V1       -> fixed authority prior
V2       -> query-aware adaptive authority prior
```

Claim Gate and grounding validation are later, classifier-independent V2 layers.

## 8. Explainability and diagnostics

Batch 2 diagnostics expose the primary category, classifier version and confidence,
runner-ups, matched signal and rationale codes, fallback status, policy version, policy
authority anchor, effective authority weight, ranking components, semantic threshold, and
known unenforced policy fields. They contain no raw evidence content, credentials, signed
URLs, or private reasoning.

The required classifier metric remains Task Classification Accuracy. No additional
category-set recall metric is required.

## 9. Compatibility and limitations

- V2 evidence selection remains opt-in. Disabled callers preserve existing behavior.
- V1 fixed-weight and Baseline zero-weight paths remain available.
- Source-aware scoring changes order only after semantic eligibility.
- Task classification does not increase search, scraping, or provider calls.
- A classifier linguistic error can affect ranking preference, but not claim safety.
- Publication freshness, publisher independence, and source-role requirements are not
  claimed as enforced until later models provide the required structured evidence.
- Claim Gate, grounding validation, and benchmark execution remain later checkpoints.

## 10. Frozen specification register

V2.2 freezes:

1. the unchanged six-category taxonomy and classifier diagnostic schema;
2. primary-category-only adaptive weighting;
3. the six unchanged category weight anchors;
4. neutral fallback `w=0.20`;
5. confidence and runner-ups as diagnostics with no weighting effect;
6. semantic eligibility before `SourceAwareScorer`;
7. no classifier-caused extra retrieval;
8. `EvidencePolicy` metadata retention with authority-weight-only Batch 2 enforcement;
9. classifier-independent high-risk claim minimums;
10. unchanged cases, split, cutoff, Required Units, claim rules, metrics, thresholds, and
    V1 history.

A later semantic change requires a new version, change note, and dataset hash. The canonical
dataset hash is recorded outside the dataset in the V2.2 change note, benchmark protocol,
and freeze test to avoid self-reference.
