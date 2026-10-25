# V2.2 Architecture Scope-Correction Change Note

**Architecture:** `enterprise-insight-v2-architecture/2.2.0`

**Benchmark/schema:** `enterprise-insight-bench-v2/2.2.0`

**Status:** FROZEN

**Frozen on:** 2026-09-09

**Supersedes active target:** V2.1 at
`d8f210d18059f3dba20d48e6960d6a204d7bd530`

**Dataset SHA-256:** `95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`

## Decision

V2.1 proposed uncertainty-aware multi-policy routing. Architecture review found that this
added implementation and specification complexity disproportionate to the original
Query-aware Evidence Selection goal. V2.2 therefore simplifies task-aware retrieval to
adaptive authority weighting.

The active Batch 2 flow is:

```text
Query
-> ResearchTaskClassifier
-> primary ResearchTaskCategory
-> adaptive authority_weight
-> semantic candidate eligibility
-> SourceAwareScorer
-> EvidenceContext
```

Only the primary category selects a normal weight. Classifier confidence and runner-up
categories remain diagnostics and have no weighting effect. Classifier fallback or an
invalid/missing classification uses the neutral V1 weight `0.20`, even when the compatibility
diagnostic category is `technical_capability_analysis`.

## Removed active V2.1 scope

The V2.1 PolicyResolver proposal, multiple category-policy execution, broad six-policy
fallback, branch-local reranking, rank fusion, material runner-up rules, and related routing
diagnostics are not part of the active architecture and have no production implementation.
The historical V2.1 change note remains unchanged as an audit record and is superseded by
this decision.

## Preserved contracts

This correction does not change the 30 queries, category labels, 18/12 split, information
cutoff, Required Units, Required Unit strength rules, high-risk taxonomy, claim-gate mappings,
six authority anchors, quality metrics, acceptance thresholds, Baseline definition, V1
definition, or any frozen V1 artifact or result.

The typed `EvidencePolicy` model remains. In Batch 2, only `authority_weight` is enforced by
retrieval ranking; its other fields are metadata and downstream guidance. Task classification
does not authorize claims or weaken classifier-independent high-risk claim minimums.

## Implementation boundary

Batch 2 implements adaptive weighting over the existing semantic-filter-first
`SourceAwareScorer` path. Claim Gate, Grounding Validator, and benchmark execution were not
started by this checkpoint. Classifier linguistic errors may affect ranking preference but
not claim safety.
