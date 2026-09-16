# V2 Information Flow Simplification

## Scope

This checkpoint restores GPT Researcher's Writer as the primary report author while retaining the existing Enterprise V2 evidence audit. It changes implementation behavior only. It does not change the frozen benchmark, Required Units, rubric, task taxonomy, EvidencePolicy definitions, or holdout data.

## Implemented flow

```text
original user question
  -> existing GPT Researcher research and complete research context
  -> existing Writer draft
  -> extract only assertions already present in that draft
  -> bind assertions to structured evidence
  -> Claim Gate and Claim-Citation Grounding
  -> render verified facts, attributed limited evidence, and premise-bound inference
  -> final report
```

The deterministic Requirement plan is constructed only after research as a coverage checklist derived from the original target and explicit dimensions. It is not supplied to research and does not replace the question supplied to the Writer. Readiness remains observable, but it does not trigger a mandatory second retrieval pass or prevent the Writer from running.

## Evidence behavior

- A Gate pass permits a claim to appear as `VERIFIED_FACT` after grounding.
- A Gate rejection cannot be revived as the rejected claim text.
- Literal, complete source passages can still appear as `LIMITED_EVIDENCE` with source attribution and limitations when they pass the existing limited-disclosure validation.
- `AI_INFERENCE` remains limited to conditional analysis whose premise claims survived the Gate and grounding checks; premise citations are rendered with the inference.
- Assertions introduced by the audit model but absent from the Writer draft are discarded and counted.
- Writer prose that was not bound and audited is not published as verified factual prose.

## Artifacts and diagnostics

Each successful V2 run now stores the original `writer_draft.md` next to `execution.json` and `report.md`. The execution record includes the Writer draft SHA-256. Diagnostics expose the number of audit claims removed because they were absent from the Writer draft.

## Validation boundary

Offline tests cover question preservation, comparison and recommendation typing, absence-only audit claim rejection, Chinese and English limited disclosure, two-sided comparison recovery, premise-bound recommendations, unbound high-risk fact suppression, HTML escaping, Writer-first execution, and removal of automatic second retrieval. No live benchmark case or holdout case was run for this checkpoint.
