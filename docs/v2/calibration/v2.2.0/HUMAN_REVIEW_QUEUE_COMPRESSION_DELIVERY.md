# V2.2 Human Review Queue Compression Delivery

## Status

**READY_FOR_HUMAN_REVIEW**

## Full Ledger

- Total items: **483**.
- Record payloads unchanged: **yes**. All factual claims, claim/citation pairs,
  Required Units, evidence-strength, independence, freshness and high-risk
  pre-annotations remain in `FULL_AI_ASSISTED_LEDGER.json`.
- Status: `AI_ASSISTED`; not final gold. All human decision fields remain unset.

## Machine-resolved Items

- No separate human action: **227 ledger records**.
- Main resolution categories: missing publication date remains `UNVERIFIED`;
  unavailable source-producing organization remains unresolved; domain/URL
  difference does not establish independence; absent first-party relationship or
  authority score does not establish primary status; clear item-level decisions
  outside the representative samples remain in the audit ledger.

These records were triaged out of the human workload, not relabeled or removed.

## Human Calibration Core

- Total: **51 tasks**.
- Required Units: all **18** (three per category), each with the exact unit,
  relevant report passage, saved evidence references, AI recommendation and reason.
- Representative clear samples: 8 claim-segmentation, 8 citation-support, 6
  evidence-strength, 6 independence and 5 freshness tasks.
- Competitive Comparison and Conflict & Credibility Resolution emitted no claims,
  so no artificial claim/citation samples were created. Competitive Comparison has
  no clear dated freshness record, so no artificial freshness sample was created.
- Per category: Factual Verification 10; Technical / Capability Analysis 10;
  Competitive Comparison 5; Trend / Market Intelligence 10; Conflict &
  Credibility Resolution 6; Enterprise Decision / Recommendation 10.

Clear samples are selected deterministically by stable review ID, not by whether
the V2 result is favorable.

## Human Adjudication Queue

- Total: **36 tasks**.
- Semantic boundary bundles: **34**. They cover every one of the **203** ledger
  records flagged for claim-segmentation, citation-entailment or high-risk semantic
  review. Records sharing one parent report passage are reviewed together, with
  every ledger ID and evidence location retained.
- Independence: **1** named-author/project relationship whose same-group versus
  independent experimental status is genuinely disputable.
- Freshness: **1** saved-date boundary case where a post-cutoff timestamp may
  belong to either the article or a recommendation sidebar.
- By category: Factual Verification 1; Technical / Capability Analysis 10; Trend /
  Market Intelligence 16; Conflict & Credibility Resolution 1; Enterprise Decision
  / Recommendation 8; Competitive Comparison 0 (no emitted semantic claims and no
  genuine non-deterministic source relationship).
- Task flags: 34 `SEMANTIC_BOUNDARY_REVIEW`; within those bundles, 31 include
  `AMBIGUOUS_SEGMENTATION`, 23 include `CITATION_SUPPORT_UNCERTAIN`, and 16 include
  `HIGH_RISK_REVIEW`; one task has `PUBLISHER_RELATIONSHIP_DISPUTABLE`; one has
  `DATE_ROLE_OR_ATTRIBUTION_DISPUTABLE`.
- Extreme metric/report triggers: 0. Failed-run adjudications: 0. All six runs
  completed, and no frozen trigger was invented merely to populate a dimension.

## Comparison

- Before human queue: **483**.
- After human workload: **87 tasks**.
- Reduction: **396 tasks (82.0%)**.
- The 87 task packets reference **256** ledger records; **227** ledger records need
  no human action. Bundling reduces duplicated context/review actions but does not
  hide or drop any referenced semantic decision.

Removed items no longer require a separate human action because the frozen rubric
already determines missing/unqualified outcomes, the item is a clear decision kept
only in the full ledger, or it is represented by the bounded calibration sample.
Semantic decisions were compressed only by grouping records governed by the same
exact parent report passage; no genuine ambiguity was suppressed.

## Required Units

All **18** Required Units remain directly human reviewable in the calibration core.

## Risk Coverage

The adjudication bundles cover all 28 high-risk ledger records and the actual
observed types: `numeric_value`, `release_status_availability`,
`comparative_claim`, `benchmark_or_performance`, and
`conflict_sensitive_claim`. The previously recorded absent types remain absent;
no synthetic review items were added.

## Frozen Contract Check

- Label/rubric semantic changes: **none**.
- New provider calls: **0**.
- Official benchmark calls: **0**.
- Holdout use: **none**.
- Agent changes: **none**.
- Complete 483-item full ledger preserved: **yes**.
- Development cases rerun: **no**.
- Final human labels created: **no**.

## Next Step

Human reviewer reviews the compressed calibration core and adjudication queue.
