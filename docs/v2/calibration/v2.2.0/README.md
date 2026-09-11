# Six-category human calibration preparation

**Delivery status: BLOCKED. Human review status: PENDING.**

This is an incomplete material-preparation package, not a ready calibration set.
Six development cases are selected and their 18 frozen Required Units are copied
exactly. No verified case-linked report or saved candidate pool was found. No live
run was attempted, no report was synthesized, and no content label was assigned.

## Available artifacts

- `CALIBRATION_CASE_SELECTION.md`: all eligible development IDs, six selected IDs,
  coverage-based rationale recorded before report inspection/execution.
- `<category>/<case_id>/case_input.json`: exact selected development record.
- `<category>/<case_id>/artifact_references.json`: explicit missing-material slots.
- `<category>/<case_id>/hashes.json`: hashes of available files; missing artifact
  hashes remain null, never empty-content hashes.
- `<category>/<case_id>/scoring_input.json`: preparation sidecar with original
  Required Units. This is not an evaluator-ready scoring input.
- `<category>/<case_id>/review_sheet.json`: 18 unassessed Required Units across
  six cases; other review sections remain empty because reports are unavailable.
- `REVIEW_ITEM_TEMPLATES.json`: fields needed for subsequent claim, citation,
  strength, independence, freshness and high-risk review; not actual annotations.
- `FROZEN_RULE_REFERENCES.json`: existing rule/policy values copied without changes.
- `HUMAN_REVIEW_QUEUE.md` and `.json`: equivalent human-readable and structured
  queues, with 24 preparation/deferral items and all human fields unset.
- `CALIBRATION_MANIFEST.json`: provenance, availability, hashes and pending status.

## Verified blocking evidence

At source commit `6f457b11a24c9b0a3eefe46559f737390b06f7f5`:

1. `benchmarks/run.py:24` fixes the dataset to V0; line 25 offers only baseline and
   source_aware. `load_cases` expects 12 V0 cases and eight development cases.
   It cannot execute the selected V2.2 IDs without a separate execution adapter.
2. `gpt_researcher/enterprise/workflow.py:207` starts live research directly.
   Line 238 explicitly states that cutoff is an instruction, not a verified
   publication-date filter. Available workflow persistence does not establish the
   raw and eligible frozen candidate artifacts specified in protocol section 2.
3. Inventory of nine `outputs/enterprise/*/execution.json` files and nine trace
   files found no case/dataset identifiers tying them to these frozen cases.
   Only identification fields and key names were displayed. Unclassified report
   bodies and evidence were not reviewed or adopted as calibration material.
4. Existing `outputs/batch9-preflight-20260911T115917Z/preflight.json` records the
   same missing candidate-fixture and calibration prerequisites. It is historical
   supporting context, not a new test result or a substitute for this inspection.

Calibration itself does not require executing all three variants or the official
comparison. The present blocker is obtaining a traceable real development report
and its preserved, cutoff-eligible evidence. A validated development-only adapter
could supply those artifacts in a separate preparation step; this task did not
modify execution code, Agent behavior, Gate/Grounding or frozen contracts. No
provider calls were spent on an unvalidated path. Credentials were not inspected;
this package does not claim credentials or providers are unavailable.

## Reviewer instructions for populated materials

Use only the saved candidate evidence associated with each report. Do not browse
for additional facts while labeling a report. Record report/evidence hashes and
exact excerpts with file/JSON locations. Keep original AI recommendations alongside
subsequent human decisions for auditability.

1. Segment atomic externally verifiable factual assertions. Preserve exact report
   spans and record factual/non-factual status. Flag ambiguous conjunctions,
   qualified assertions and distinctions between recommendation and factual
   premise. Materiality is recorded only where the existing rule requires it;
   this package introduces no new materiality threshold.
2. For every factual claim/citation pair, compare entity, scope, qualifications and
   cutoff against exact saved text. Use the existing support/conflict/unclear
   semantics; citation presence is not support. Do not award partial support to an
   atomic assertion whose substantive scope is not established. Escalate disputed
   segmentation or label mapping instead of introducing a new rubric value.
3. For every Required Unit, inspect its complete text and strength requirement.
   Partial topical mention does not pass. Missing reports here are NOT_ATTEMPTED;
   they must not be scored as failed runs or NOT_SATISFIED units. Genuine failed
   executions, if later supplied, must retain their artifacts and follow section 5.
4. Establish primary-source status using explicit content and source identity.
   Authority is only a source prior; it does not establish truth or primary status.
5. For multi-source rules, preserve producing-organization/editorial-control
   evidence and proposed group membership. Different URLs or domains do not prove
   independence. Recommend UNRESOLVED when identity cannot be established.
6. Distinguish publication date from event date. Preserve exact date evidence.
   Post-cutoff sources cannot support scoring even when reporting earlier events.
   Unknown dates fail strict freshness and are flagged in other modes. Do not
   infer dates from access time. Use verified/unverified/out_of_cutoff suggestions
   only when corresponding source material is available.
7. Apply all applicable risk and Required Unit rules without weakening them.
   `FROZEN_RULE_REFERENCES.json` preserves the union rules and the existing
   comparable-primary-evidence-per-entity override. Source strength alone never
   replaces claim support review. Do not copy runtime gate verdicts as gold labels.
8. Escalate ambiguous items, actual extreme scores, failed runs and high-risk
   violations. Use UNCERTAIN, AMBIGUOUS_SEGMENTATION,
   CITATION_SUPPORT_UNCERTAIN, INDEPENDENCE_UNRESOLVED,
   FRESHNESS_UNVERIFIED, HIGH_RISK_REVIEW and EXTREME_METRIC_TRIGGER as
   appropriate. No extreme metric was computed here; no numeric trigger is invented.

All recommendations must retain `AI_ASSISTED_RECOMMENDATION`. Human identity,
timestamp, decision and adjudication note remain null until supplied by the human
reviewer. Confidence never promotes a recommendation into a final label. These
sidecars must not be imported as reviewed benchmark annotations.

## Coverage and cost

Planned Required Unit coverage spans six of eight risk types. Actual report risk
coverage is unknown for all eight types because no reports are present. The two
types absent from selected Required Units are `market_metric` and
`superlative_or_ranking`; naturally occurring report claims may later cover them.
Do not assert that the six reports cover any risk until reports actually exist.

There are 24 open preparation/deferral items: six missing-material items and 18
unassessable Required Units. There are zero completed content annotations and zero
confident content-label recommendations. All 24 require material resolution and
later human review. Review queue counts do not measure annotation progress.

Development calibration provider calls: 0; cost incurred by this task: USD 0.
Official benchmark provider calls: 0; cost incurred by this task: USD 0.
No holdout cases or outputs were reviewed, annotated or executed. No frozen
dataset, rubric, Agent, Gate/Grounding or benchmark schema was changed.
