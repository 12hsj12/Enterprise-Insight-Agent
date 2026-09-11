# Qualification Coverage Integration Delivery

## Status

PASS.

This is a bounded integration completion over the existing Batch 8 writer and
the existing `ClaimEvidenceQualification`. It is not a new architecture batch,
EvidencePolicy, Gate policy, taxonomy, or benchmark run.

## Root Cause

The live Claim/Evidence pipeline already produced Claims and explicit
support/conflict/unclear links, but automatic authoring stopped at those fields.
The existing Gate therefore received no required entity/side obligations and no
claim-scoped qualification records. High-risk rules correctly treated missing
primary, independence, entity, material-side, and adjudicator metadata as unmet.

## Runtime Metadata Audit

### Explicit metadata available

The three pre-change smoke artifacts persisted Evidence ID, sub-query, title,
URL, content, source type, and retrieval diagnostics. The real scrape objects
contained URL, title, raw content, and images. Prefetched retrievers can also
return explicit publisher, source organization, source owner, author,
publication date, and source type, but the compression boundary previously
discarded those optional fields.

### Conservatively derivable metadata

- Exact explicit owner/source-organization/publisher values can be normalized
  into an execution-scoped opaque editorial-control group ID.
- A source-producing organization can be accepted from content only when the
  same writer returns an exact content anchor plus an explicit publisher,
  copyright, organizational-byline, issuer, or editorial-control relationship.
- Bounded entity and material-side labels can be converted to deterministic,
  execution-scoped opaque IDs after reference validation.
- Explicit relation-level entity and side references can be mapped to the
  existing qualification fields.

### Unavailable metadata

The live scraper did not expose structured publisher/source-owner metadata for
the final A/B/C runs. No final run contained a sufficiently explicit accepted
content relationship for source-producing organization identity. Independence,
primary-source, and independent-adjudicator qualification therefore remained
unavailable.

### Rejected weak proxies

URL hostname, different domains, authority score, final/search score, citation
presence, generic source type, page-title branding, ordinary organization
mentions, `X says/reported`, and a third-party reference to an organization's
press release are not source identity, primary status, independence, or
adjudicator evidence.

## Integration Design

The retrieval/compression path now preserves an allowlist of explicitly supplied
source metadata. The existing single structured writer call adds bounded source
identity candidates, claim entity/side references, and evidence-to-entity/side
associations. Registration validates all IDs and content anchors, builds stable
opaque IDs, and emits only the existing `ClaimEvidenceQualification` model.

The execution artifact adds coverage counts, source-identity resolution outcomes,
qualification-field provenance, dropped-input counts, and an opaque-ID-to-label
reference map. Existing Gate results continue to expose resolved obligations and
unmet requirements. There is no extra LLM call.

## Claim-side Context

- Comparative Claims receive `required_entity_ids` only when structured
  authoring supplies at least two valid explicit entity references.
- Conflict-sensitive Claims receive `required_material_side_ids` only when
  structured authoring supplies at least two valid explicit material sides.
- Entity IDs are stable within an execution; side IDs are stable within a Claim.
  Both retain mappings to their writer reference and bounded original label.
- No free-text regex NER or conflict ontology was added.

## Evidence Qualification

- `independence_group_id`: derived only from an accepted explicit
  source-producing/editorial-control organization; same normalized organization
  produces the same execution-scoped group.
- `is_primary_source`: true only for a support relation explicitly marked for an
  entity when every entity supported by that evidence is the same accepted
  source organization. This prevents a source primary for A from becoming
  primary for B through the model's evidence-level boolean.
- `supported_entity_ids`: mapped only from explicit relation-level entity
  references authored in the existing structured call.
- `material_side_ids`: mapped only from explicit relation-level side references;
  `relation=conflict` never implies all sides.
- `is_independent_adjudicator`: true only with an exact content statement that
  explicitly states independence/neutrality/third-party status and names the
  accepted source organization plus every conflict party. No final live run met
  this rule.

## Safety

Gate thresholds, risk taxonomy/mapping, evidence-strength rules, missing metadata
semantics, `union_without_weakening`, and Grounding behavior are unchanged. URL,
domain, authority, ranking, citation, and high-authority publisher status are not
promoted into unsupported qualification. Unknown evidence/entity/side references,
duplicate relation ambiguity, conflicting identities, unverifiable anchors, and
cross-entity primary ambiguity are dropped and counted.

## Tests

Deterministic qualification integration:

```text
.venv/Scripts/python.exe -m pytest tests/test_qualification_coverage_integration.py -q
13 passed
```

Gate/Grounding/integration focused regression:

```text
.venv/Scripts/python.exe -m pytest tests/test_qualification_coverage_integration.py tests/test_enterprise_integration.py tests/test_claim_gate.py tests/test_grounding_validator.py -q
80 passed
```

Final Batch 2-8 regression: 360 passed.

Broad offline suite: 784 passed, 2 skipped, 19 failed in the shared process.
Seventeen of the 19 failures passed when rerun in fresh pytest processes, showing
known order-dependent `sys.modules` test-stub pollution. The remaining two
unrelated logging tests instantiate live OpenAI embeddings without credentials
and fail offline for missing credentials.

## Live Re-smoke Comparison

The requests reused the same topics and cutoff as the pre-change A/B/C smoke.
Retrieval and generation remain nondeterministic, so Claim/link totals differ.
Counts come from each structured execution artifact.

| Type | Qualification records / linked pairs | Primary | Group records / distinct groups | Required entity IDs / supported associations | Required side IDs / side associations | Adjudicator | Gate EMIT/HEDGE/OMIT |
|---|---:|---:|---:|---:|---:|---:|---:|
| A factual, before | 0 / 42 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 | 0 / 0 / 15 |
| A factual, after | 0 / 19 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 | 0 / 0 / 9 |
| B comparison, before | 0 / 65 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 | 6 / 0 / 21 |
| B comparison, after | 47 / 64 | 0 | 0 / 0 | 24 / 85 | 0 / 0 | 0 | 3 / 0 / 16 |
| C conflict, before | 0 / 76 | 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 | 0 / 0 / 25 |
| C conflict, after | 71 / 107 | 0 | 0 / 0 | 31 / 88 | 16 / 35 | 0 | 0 / 0 / 39 |

C authored explicit sides for eight conflict-sensitive Claims, and all eight
satisfied the Gate's material-side coverage requirement. All still lacked an
independent adjudicator; other high-risk requirements were also unmet, so the
final Gate safely omitted them. The run did not optimize for EMIT rate.

Final artifact task IDs:

- A: `525c915e-9953-414c-880c-ccdf19999873`
- B: `7f43d01c-d639-48b9-abff-b3dde9e1918c`
- C: `514acee5-e31b-4537-b501-3a06f5d6aaf8`

Final-run provider cost was USD 0.34522702, 0.50492900, and 0.68598082,
respectively (USD 1.53613684). An earlier three-run integration smoke exposed
and rejected an over-broad source-identity anchor rule before final acceptance;
those runs cost USD 1.71635468. Total provider cost for this completion was
therefore USD 3.25249152. Rejected-run results are not used in the comparison.

## Frozen Contract Check

Batch 2-8 semantics remain unchanged. No frozen V1 file, frozen benchmark case,
Required Unit, metric definition, taxonomy, policy, Gate rule, or Grounding rule
was modified. No formal 12-case benchmark was run.

## Files Changed

- `gpt_researcher/evidence/models.py`
- `gpt_researcher/context/retriever.py`
- `gpt_researcher/context/compression.py`
- `gpt_researcher/skills/researcher.py`
- `gpt_researcher/enterprise/integration.py`
- `tests/test_qualification_coverage_integration.py`
- `docs/v2/BATCH8_DELIVERY.md`
- `docs/v2/BATCH8_LOCAL_SMOKE.md`
- `docs/v2/QUALIFICATION_COVERAGE_INTEGRATION_DELIVERY.md`

## Scope Check

No Judge, semantic entailment evaluator, qualification agent, extra LLM call,
NER framework, organization database/graph, policy engine, dashboard, recursive
retrieval loop, or architecture pillar was added.

## Remaining Limitations

- The default live web scrape path usually supplies title/URL/content but not
  explicit publisher/source-owner metadata, so conservative primary and
  independence coverage can remain zero.
- Content anchors can only qualify producer identity when they explicitly state
  the required relationship. Executive affiliation or company attribution alone
  remains insufficient.
- Entity and material-side associations remain bounded writer-authored inputs,
  not independently judged entailment.
- Retrieval and authoring nondeterminism prevent raw Claim-count or EMIT-count
  changes between smoke runs from being interpreted as quality improvement.
