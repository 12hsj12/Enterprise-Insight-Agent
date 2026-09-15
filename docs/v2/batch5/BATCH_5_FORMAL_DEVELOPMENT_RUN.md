# Batch 5 Formal Development Run

## Decision

`DETERMINISTIC_BLOCKER_REMAINS`

This is the one authorized six-case development execution after the Batch 5
preflight repair. It is not a valid effectiveness result set: only FV produced
a final report. The remaining five cases all completed search and retrieval,
but failed in the report stage with `ValueError`, surfaced by the API as
`internal_invariant` / HTTP 500. No retry was made because these were not
provider, network, or search-provider failures.

## Execution Identity

- Source commit: `d6d3a9c8d8c8718eb5c5458f7eaf58da6cdf8548`
- Runtime comparison: no `gpt_researcher` or `backend` change relative to
  Batch 4 accepted commit `ab1473d44cf056e1c8d3ae0187cad0f4d718ab98`
- Output directory:
  `outputs/batch5-development-effectiveness-valid-20260915T080000Z`
- V2 request flags for every task:
  `enable_v2_execution=true`, `enable_v2_evidence_selection=true`
- Holdout runs, searches, evaluation, and tuning: `0`

## Case Record

| Case | Task ID | Status | Report | Runtime s | Search calls | Retry |
| --- | --- | --- | --- | ---: | ---: | --- |
| EIV2_FV_001 | c14658fe-f851-431d-b359-3dd6792f09c9 | completed | present | 145.533 | 5 | no |
| EIV2_TC_001 | 38b40221-cf96-4474-9730-0399f169114d | failed: internal_invariant | absent | 176.171 | 4 | no |
| EIV2_CC_001 | acc92822-6d50-4f83-8612-70b9ac10ef82 | failed: internal_invariant | absent | 214.007 | 5 | no |
| EIV2_TM_003 | 9d86343a-6fe7-4989-9926-4881a8230621 | failed: internal_invariant | absent | 216.814 | 7 | no |
| EIV2_CR_003 | 183b5ad8-e183-45fe-9f8b-01a2c532e556 | failed: internal_invariant | absent | 207.472 | 6 | no |
| EIV2_ED_002 | 0fcf554b-0f56-4911-a179-2ca89a45c90f | failed: internal_invariant | absent | 213.254 | 7 | no |

All five failed traces record successful search/retrieval work and a report
span with `error_type=ValueError`; raw task records and traces are retained in
the output directory. The API records only the exception class, not a message
or traceback, so this run establishes the stage and deterministic recurrence,
not the precise source line.

## Observed Retrieval Facts

- Total search calls: `34`; retrieval calls: `32`; selected evidence: `255`.
- Second retrieval triggered on FV, CC, TM, CR, and ED: `10` queries,
  `83` additional candidates, `71.457s` additional search latency.
- FV recovered one initially not-ready requirement; CC recovered one. TM, CR,
  and ED did not make their initially not-ready requirements ready.
- FV is the only completed report. Its layered-output record contains
  `12 VERIFIED_FACT`, `2 LIMITED_EVIDENCE`, `0 AI_INFERENCE`, and
  `0 UNRESOLVED`; its runtime estimated cost is `$0.91711284`.

## Evaluation Boundary

The frozen strict Required Unit result remains `Before: 1/18`. `After` is
`N/A`: five of six required final reports are absent, so scoring an apparent
partial result as a six-case effectiveness measurement would be invalid.
Likewise, category utility, cross-case safety, readability, and Batch 1--4
effectiveness cannot be concluded from this run.

The next action is a focused, independent diagnosis of the report-stage
`ValueError`, followed by repair review and a newly authorized experiment.
This record does not authorize a retry, a holdout run, or any implementation
change.
