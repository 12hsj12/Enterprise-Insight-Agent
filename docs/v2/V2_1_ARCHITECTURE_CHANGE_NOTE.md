# V2.1 Architecture Re-freeze Change Note

**Status:** FROZEN

**Decision date:** 2026-09-09

**Revision baseline:** `b0caaed358dbb2d5f3972041c73586055b30d2d7`

**Original V2 freeze checkpoint:** `25be9cd57c44a4494c220a70baef043532fda2cb`

## Version transition

- Previous architecture: `enterprise-insight-v2-architecture/2.0.0`
- New architecture: `enterprise-insight-v2-architecture/2.1.0`
- Previous benchmark protocol/schema: `enterprise-insight-bench-v2/2.0.0`
- New benchmark protocol/schema: `enterprise-insight-bench-v2/2.1.0`
- New independent resolver contract: `enterprise-insight-policy-resolver/1.0.0`

The historical 2.0 freeze commit is not rewritten.

## Reason

Independent adversarial Architecture Decision Review identified single-label classifier
routing as a brittle safety dependency even after deterministic classification reached
30/30 on the frozen set. A correct frozen-set primary label does not prove that every future
request is structurally unambiguous, nor should a retrieval-preference classifier authorize
factual claim emission.

## Change

The deterministic, query-only classifier is retained with its primary category, confidence,
signals, runner-ups, rationale codes, fallback behavior, and precedence. V2.1 adds a typed,
uncertainty-aware PolicyResolver; bounded multi-policy evidence routing over one shared
semantic candidate pool; branch-local reranking; deterministic round-robin fusion; explicit
policy-obligation preservation; and a claim-level safety boundary that is independent of
the classifier category.

Classifier errors may change retrieval preference. They may not weaken high-risk claim
minimum evidence rules, Required Unit rules, policy obligations, or the global information
cutoff.

## Unchanged frozen semantics

V2.1 does not change:

- the six-category business taxonomy or deterministic classifier precedence;
- any of the 30 queries, category labels, or 18 development / 12 holdout assignments;
- the 2026-09-05 information cutoff;
- Required Units, their evidence-strength rules, or applicable high-risk types;
- EvidencePolicy values, authority weights, source roles, freshness windows, corroboration,
  primary-source, or publisher-organization independence rules;
- high-risk taxonomy, `risk_to_minimum_rule`, or claim-gate values;
- headline metric definitions, Baseline, V1, acceptance thresholds, or failure conditions;
- V1 artifacts, annotations, results, frozen commit, or published history.

## Dataset re-freeze

The canonical SHA-256 of the exact final bytes of
`benchmarks/dataset/enterprise_insight_bench_v2.json` is:

`956519ed56ecabdba6c8e3ad059b48785772be9b63e1a937485433a204cc3dd5`

The hash is recorded outside the dataset to avoid self-referential hashing. The freeze test
recomputes the file-byte hash and compares it to this literal.

The following canonical JSON section hashes were captured from revision baseline
`b0caaed358dbb2d5f3972041c73586055b30d2d7` and remain literal preservation contracts in
`tests/test_v2_spec_freeze.py`:

| Immutable section | SHA-256 |
|---|---|
| `cutoff_date` | `fcd1b035a403732fcb30948679a11651f4a5fb3c2f89fea3e4f990b7deb3db29` |
| `categories` | `4b01f0e418b0fee8be0a39a3ab7056c6da63b279984160561038e92b34656442` |
| `claim_gate_rules` | `c3a3cccaa34e86a1b09658ec202a02e68bfe43f941257e766332c70f2fd2d1f9` |
| `evidence_policies` | `69ee932ac1915f5ef561b35377870b64af10af370661cdfef156229a60a901d4` |
| `acceptance_criteria` | `cf20780e12f69a341805805d35788e02cd024052630bd4d08864202dc174de3c` |
| `metric_contracts` | `8c9cae9d798ecd6b4041524b9dd686c61b46e3485554d03c520e8d5224097a4f` |
| `cases` | `a7533929c245b3146954d0ea2bbb47a602a280c541d33e08cdf1658dfef8e676` |

Canonical section serialization uses UTF-8 JSON with sorted keys, no insignificant
whitespace, and non-ASCII characters preserved. The complete `cases` hash covers every
query, label, split, case cutoff, Required Unit, evidence-strength rule, and high-risk type.

## Scope boundary

This checkpoint changes specification and freeze artifacts only. It does not implement
PolicyResolver runtime code, modify Batch 2 evidence-selection production code, begin Batch
2R, begin Batch 3, execute live search, call a paid provider, or rerun V1 benchmarks.
