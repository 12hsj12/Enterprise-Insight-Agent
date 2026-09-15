# V2 Utility Correction Batch 5 Delivery

## Decision

`BLOCKED`

The six-case development effectiveness experiment is invalid. `EIV2_FV_001` completed twice, violating the one-formal-run rule; each process then started `EIV2_TC_001` before being stopped, and none of the other five cases has a final artifact. It is therefore not valid to calculate an after score, safety metrics, output utility, or a new failure map.

## Experiment Identity

- Source commit: `ab1473d44cf056e1c8d3ae0187cad0f4d718ab98`
- Benchmark schema: `enterprise-insight-bench-v2/2.2.0`
- Dataset SHA: `95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`
- Cutoff: `2026-09-05`
- Cases: `EIV2_FV_001`, `EIV2_TC_001`, `EIV2_CC_001`, `EIV2_TM_003`, `EIV2_CR_003`, `EIV2_ED_002`
- Provider configuration: DeepSeek V4 Flash through the configured OpenAI-compatible provider; Tavily search; `all-MiniLM-L6-v2` embedding.

The runner’s no-provider-call preflight passed and re-verified the frozen six development cases, 18 Required Units, and dataset hash. The frozen calibration package also passed its offline integrity verifier.

The two completed FV task records set `enable_v2_evidence_selection=false` while setting `enable_v2_execution=true`. That is an additional Batch 5 configuration noncompliance: this acceptance required the explicit final evidence-selection path to be enabled. Neither FV artifact is an official full-chain Batch 5 result.

## Execution Record

Attempt 1 completed `EIV2_FV_001` from `2026-09-15T10:22:42.851393Z` to `2026-09-15T10:25:43.638668Z`, producing a report, execution record, trace, selected evidence, Gate results, Grounding results, and layered output records. Its trace duration was `180.78108030000294` seconds and its runtime cost estimate was `$0.68677524`. It then began `EIV2_TC_001`.

Attempt 2 completed `EIV2_FV_001` from `2026-09-15T10:23:34.517479Z` to `2026-09-15T10:26:27.544098Z`, again producing the full FV artifact set. Its trace duration was `173.01047259999905` seconds and its runtime cost estimate was `$1.0144089`. It then began `EIV2_TC_001`.

The second FV run was not an allowed infrastructure retry: at the time it was initiated, the first FV process had not yet been observed to finish, but its raw artifact proves that it did finish. This is a protocol-violating duplicate rather than a quality result to select. Both processes were stopped once the duplicate was independently identified; no third provider call was made. The ignored raw directories and their SHA-256 anchors are listed in [the machine-readable record](BATCH_5_DEVELOPMENT_EFFECTIVENESS.json).

## Required Unit Results

### Before

`1/18`

### After

`N/A — no valid, single-run six-case post-correction result set exists.`

Per-category results, deltas, and the requested before/after table are also `N/A`; assigning `NOT_SATISFIED` or carrying forward `1/18` would misstate a new measurement.

## User-Visible Utility

Not measurable for the six-case experiment. Two non-evaluable FV reports exist, but CC, CR, ED and the other two categories have no post-correction report.

## Batch 3 Retrieval Effect

Not measurable for six cases. FV raw artifacts contain diagnostics, but they cannot establish the requested six-case effect after the duplicate-run and configuration failures.

## Safety

Not established for the six-case experiment. FV raw artifacts contain generated claims, Gate results, Grounding results, layered-output records, and inference records, but no independent safety scoring has been performed and the experiment is incomplete. This is not a claim that leakage is zero.

## Readability

Not measurable for six cases: two non-evaluable FV reports exist, but the required six reports do not.

## Remaining Failure Map

The frozen map is preserved without alteration. A post-correction map cannot be derived without a valid, single-run six-case post-correction result set; see [POST_CORRECTION_DEVELOPMENT_FAILURE_MAP.md](POST_CORRECTION_DEVELOPMENT_FAILURE_MAP.md).

## Cost and Latency

`actual_provider_bill = unavailable`. FV runtime cost estimates were `$0.68677524` and `$1.0144089`; FV trace durations were `180.78108030000294s` and `173.01047259999905s`. Token usage, search cost, and valid six-case/second-retrieval aggregates are unavailable. Zero must not be substituted for unknown.

## Integrity

- No runtime code was changed.
- No Gate, Grounding, policy, scorer, freshness, independence, primary-source, qualification, requirement-planner, readiness, or layered-output setting was changed.
- Holdout execution, evaluation, annotation, and search: `0`.
- Quality reruns: `0`; nevertheless, one protocol-violating duplicate FV execution occurred.
- Holdout identifiers were not present in the Batch 5 raw output directories.

## Final Interpretation

1. Batch 1–4 cannot be judged from this run.
2. Strict RU change cannot be measured.
3. User-visible report improvement cannot be measured.
4. Safety cannot be established for the invalid/incomplete experiment; FV artifacts exist, but no independent six-case safety scoring was performed.
5. Further feature development is not justified by this evidence. The immediate issue is invalid experiment control and configuration: a full rerun requires an execution supervisor that confirms process state before an infrastructure retry is authorized and an explicit full-chain configuration assertion.

## Final Recommendation

`STOP_AND_REVIEW_ONE_DETERMINISTIC_BLOCKER`

The blocker is experiment execution control/configuration rather than a demonstrated Agent runtime-code defect. Do not use either FV result for effectiveness claims. Before authorizing a new six-case experiment, establish a supervisor that waits for/inspects a task terminal state before treating an invocation as a no-artifact infrastructure failure, and assert both the official V2 execution and evidence-selection flags. Do not start holdout.
