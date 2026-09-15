# Batch 5 E2E Blocker Resolution

## Decision

`READY_FOR_FINAL_BATCH_5_RERUN`. This repair was diagnosed and smoke-tested on
development case `EIV2_TC_001` only. It is not a six-case effectiveness result,
does not score Required Units, and does not touch holdout.

## Captured Failure

The one diagnostic TC run failed with HTTP 500 in `register_proposal` at
`gpt_researcher/enterprise/integration.py:434` (diagnostic source line):

`ValueError: Comparative requirement claim lacks comparative risk type`

Its R2 Requirement was `COMPARATIVE`. The structured writer supplied proposal
`R2_ivfflat_tuning` with `risk_types=[]`, alongside valid R2 atoms. The old
registration invariant raised on that one atom before any Gate event, so the
entire report failed. The saved diagnostic input reproduces the exact exception
offline. FV's saved execution has four `FACTUAL` Requirements and no comparative
Requirement, so this particular guard was not reached there.

After excluding the invalid comparative atom in an offline replay, a second
boundary violation surfaced: the writer cited unique prefixes such as
`ev_87d2` for the supplied opaque ID `ev_87d217fa2e07e448`. This would raise
`Unknown qualification evidence ID` before Gate. The diagnostic TC response
used 19 such unique prefixes across 25 supplied evidence objects. No inference
from text, URL, authority, or source type is used for ID expansion.

The original five failures share the report path, but their writer responses
were not persisted. Their identical root causes are **not proven** by this TC
diagnosis.

## Repair

`register_proposal` now excludes an atom bound to a comparative Requirement
when its writer proposal omits `COMPARATIVE_CLAIM`. It excludes that atom before
stable claim identity and link registration. Source excerpts for it cannot bind,
and inference references to it become invalid. Other valid atoms continue.

The same boundary expands a writer evidence reference only when it is a unique
prefix of a supplied 16-hex runtime evidence ID and contains at least three hex
characters after `ev_`. Ambiguous and unknown references remain unresolved and
fail closed. The plan and execution record dropped-atom and resolved-prefix
counts. Gate, Grounding, Requirement Planner, and retrieval policy were not
changed.

The opt-in diagnostic runner saves scrubbed structured writer inputs, stage,
message, traceback, and current IDs. It does not save prompts or credentials.
Normal API behavior is unchanged; the diagnostic artifact is local generated
output and is not committed.

## Verification

- Before repair: TC diagnostic structured input raised the captured
  `ValueError` offline.
- After repair: the same structured input completed registration, Gate,
  Grounding, and report rendering with provider calls `0`, search calls `0`.
  It registered 23 atoms, excluded 3 invalid comparative atoms, resolved 105
  writer prefix occurrences, and rendered 3 factual records plus 20 limited
  disclosures.
- Post-fix TC live smoke: HTTP 200; final report and execution persisted.
  Task `4c7d679d-0906-4d50-b246-f12d09cb10a6` generated a 5,298-byte report
  with SHA-256
  `69824c547ca1e41657e72c785eca290cbc3ecebe1dc0df9406106aaedfee3619`.
  Runtime recorded 5 search events, 6 retrieval events, and estimated provider
  cost `$0.86988176`. The final execution has 11 factual records, 2 bound
  inferences, 1 unresolved Requirement, 4 excluded comparative atoms, and
  no prefix expansion needed. Every factual record has Gate `EMIT`; all
  Grounding statuses are `PASS`. The excluded atoms' exact text is absent from
  the report.
- Affected offline regression: 270 tests passed. Compile and
  `git diff --check` passed.

Local diagnostic directories:

- `outputs/batch5-blocker-diagnostic-tc-20260915`
- `outputs/batch5-blocker-postfix-tc-20260915`

## Limitation

This smoke demonstrates report completion under one new TC retrieval/writer
sample. It does not establish five-case shared causality or measured Batch 5
quality. The final frozen six-case development rerun requires separate operator
authorization and must start from the beginning; no diagnostic run is reused
for scoring.
