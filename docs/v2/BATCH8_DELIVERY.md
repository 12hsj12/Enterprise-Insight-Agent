# Batch 8 End-to-End Integration Delivery

## Status

**PASS.** Independent review passed after both bounded repairs. This qualifies
the Batch 8 integration, not completion of all V2 benchmark work. No live research
or paid benchmark was run in this batch. The final commit hash and remote sync
verification are recorded in the delivery response.

## Branch / Commit

- Branch: `feat/evidence-v2`.
- Verified starting HEAD: `a31d159af248371e88873ac2b5c7c4ab3a8dba69`.
- Frozen V1 local/remote branch: `0e3c6b8643db499936312f4ff24e6af1641409e4`.
- Delivery checkpoint: the commit containing this document and its integration tests.

## Real Execution Path

`main:app` loads the existing backend FastAPI application. The existing
`POST /api/enterprise/tasks` creates `IntelligenceWorkflow`, which constructs the
real `GPTResearcher`. `conduct_research()` invokes `ResearchConductor`: research
outline, retriever search, `BrowserManager.browse_urls`, and `ContextManager` web
compression. `ContextCompressor` selects chunks using existing semantic/authority
ranking and returns `EvidenceContext`. The context manager registers selected
Evidence, assessments and ranking diagnostics on the researcher.

`enable_v2_execution=true` wires those selected records to the Claim pipeline.
The existing `ReportGenerator` gains a small structured authoring method using
the same researcher config, provider utility and cost callback. The Enterprise
workflow performs deterministic final rendering after Gate and Grounding.
The legacy report, frontend and WebSocket paths retain their existing behavior;
the supported V2 entry is the existing Enterprise API, not a separate demo agent.

## End-to-End Flow

Query → GPTResearcher research/search/scrape → selected Evidence → assembled
EvidenceContext → structured authoring/explicit reviewed plan → stable Claim
registration → ClaimEvidenceBinder → ClaimGate → controlled GeneratedClaimRecord
→ GroundingValidator on final citation subset → zero/one local repair application
→ optional post-repair validation → final Markdown and execution artifact →
completed ResearchTrace → existing EvaluationAdapter association.

## Integration Changes

| Integration point | Required change |
|---|---|
| Request/workflow | Opt-in V2 execution and optional explicit ClaimPlan; automatically enables existing task-aware selection |
| ReportGenerator | Thin structured proposal authoring hook, using existing LLM configuration/cost accounting |
| integration.py | Bounded typed adapter, registration/binding, existing Gate/Grounding calls, deterministic rendering |
| Workflow lifecycle | Default trace creation/export, core artifact export before completion, failure trace, byte-exact report hash |
| Enterprise API | Successful/failed EvaluationCaseResult and trace/artifact association in existing TaskRecord |
| Tests/documentation | Offline production-path fixture, failure tests, local API smoke instructions |

## Claim Production

Previously the real report writer returned only Markdown. Batch 3–7 types did
not themselves produce runtime claims. The new authoring hook requests one JSON
proposal of at most 60 atomic claims with frozen risk labels and `is_material`.
The adapter computes existing V2 stable IDs from scope/text for all claims before
creating links. The binder receives the full registered claim/evidence set.
Duplicate registration, mismatched link ownership and unknown IDs fail closed.
There is no free-text extraction subsystem or additional semantic judge.

Writer relations and risk labels are explicit authoring inputs, not independent
proof of entailment or complete risk detection. The deterministic validation
retains this limitation; no benchmark quality improvement is claimed.

## Evidence Binding / Qualification

Relations are supplied explicitly as support/conflict/unclear; citation choice
does not create support. Authority remains a source prior only. Stable Evidence
IDs and ranking are unchanged. At Batch 8 delivery time, the writer schema could
not supply qualifications. The later Qualification Coverage Integration extends
that same bounded writer call with fail-closed entity/side associations and
explicit source-identity anchors; it does not change the Gate contract. Optional
reviewed `claim_plan` inputs continue to supply existing qualifications and gate
contexts; unknown qualification evidence IDs are rejected. Qualification is
kept per Claim for both Gate and Grounding, so primary status, independence,
entities, conflict sides and adjudicator status cannot leak across claims.
Missing qualification/date data remains missing. No domain-based inference exists.
See `QUALIFICATION_COVERAGE_INTEGRATION_DELIVERY.md` for the implemented boundary.

## Gate / Generation Behavior

- EMIT: create factual record with the selected citation subset.
- HEDGE: create hedged record and render a visible unconfirmed-assertion prefix.
- OMIT: generate no final record.
- RETRIEVE_MORE: remains unresolved and generates no final record. Additional
  retrieval attempts are explicitly zero; no safe claim-specific continuation
  was added to the existing broad research pass.

Every registered claim is gated, including nonmaterial ones. Resolved obligations
are persisted unchanged. Final text is the registered claim text with Markdown
escaping; there is no later unconstrained rewrite that can introduce untracked
claims or citations. Missing evidence produces failure before authoring; zero
eligible claims produces an explicit abstention report.

## Grounding / Repair

Each generated claim is validated against its actual chosen citation subset,
explicit links, claim-specific qualifications and persisted Gate obligations.
Publication audit metadata is optional; absent dates are unverified. The existing
validator creates repair actions. Plans are combined into at most one application
over the report's records, then one revalidation. Allowed actions remain only
remove_claim, mark_claim_hedged and remove_invalid_citation. A remaining failure
stops export. Grounding never triggers retrieval or another LLM call.

## Trace Integration

One active recorder surrounds research, authoring, Gate, generation, Grounding,
repair and core artifact export. Existing ContextManager/Gate/Grounding/repair
hooks emit existing event categories; the authoring hook uses the existing report
timing stage. Completion includes final claim count and output reference; failures
complete a failed trace without a successful output reference. Trace export and
snapshot remain fail-open. No new trace semantics or event taxonomy was needed.

## Evaluation Integration

`IntelligenceResult.to_evaluation_case(case_id)` and API `evaluation_result` use
the existing Batch 6 adapter directly. They associate final artifact, trace ID,
actual trace artifact reference, observed cost, Gate/Grounding records and repair
counts. API failures expose a bounded failed EvaluationCaseResult with no output
artifact reference. Unknown benchmark annotations and unavailable global source
qualification/reliability aggregates remain unknown. Evaluation never parses trace
to compute metrics; no Baseline metrics or benchmark acceptance result is invented.

## Artifacts

- `outputs/enterprise/<task_id>/report.md` — final UTF-8 Markdown.
- `outputs/enterprise/<task_id>/execution.json` — structured execution, trace/run
  identity, final artifact reference and SHA-256 of actual report bytes.
- `outputs/enterprise/traces/<trace_id>.json` — one existing trace artifact.
- Existing task API/store — result and evaluation association; no new database.

The audit file contains structured claim text but no duplicate report body.
Core export writes audit then a pending report, renaming to final only after the
write succeeds. Export failures may leave diagnostic partial files, never a
successful task result. Existing run directories are not overwritten.

## Manual Local Smoke Path

See [BATCH8_LOCAL_SMOKE.md](BATCH8_LOCAL_SMOKE.md) for exact PowerShell commands,
provider configuration, factual/comparison/conflict examples and artifact inspection.
Entry: `.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1`,
then POST to `/api/enterprise/tasks` with `enable_v2_execution=true`.
No credentials were read into output, changed or committed. No paid execution was
performed; the fixture's 0.125 USD cost is explicitly synthetic test input.

## Tests

Network kill-switch: `$env:GPTR_BLOCK_NETWORK='1'`.

Focused and Batch 2–7/V1/persistence/freeze regression command:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_enterprise_integration.py tests/test_batch8_evaluation_compat.py tests/test_enterprise_workflow.py tests/test_enterprise_api.py tests/test_enterprise_persistence.py tests/test_v2_task_policy.py tests/test_v2_classifier_boundaries.py tests/test_v2_evidence_selection.py tests/test_claim_evidence_binding.py tests/test_claim_gate.py tests/test_grounding_validator.py tests/test_evaluation_harness.py tests/test_research_trace.py tests/test_enterprise_trace.py tests/test_enterprise_evaluation.py tests/test_v2_spec_freeze.py tests/test_evidence_reliability.py tests/test_evidence_consistency.py tests/test_source_aware.py tests/test_source_aware_config.py -q
```

Measured after the integration/hash repairs: **380 passed**, 3 warnings.
The production-path fixture mocks external services and registry discovery but
executes real GPTResearcher, ResearchConductor, ContextManager, compression,
ReportGenerator, Gate, Grounding and API code.

```powershell
.venv/Scripts/python.exe -m compileall -q gpt_researcher benchmarks tests backend/server
git diff --check
```

Both passed. Broader compileall including all `backend` found the unchanged
`backend/report_type/deep_research/example.py:291` Python 3.11 f-string backslash
syntax error. This unrelated example was not modified.

Full offline command: `.venv/Scripts/python.exe -m pytest -q --tb=short`.
Final measured outcome: **771 passed, 19 failed, 2 skipped**, 4 warnings, 63.95s.
Compared with the supplied Batch 7 baseline (747/19/2), 24 new tests passed and
the inherited failure count is unchanged. The 19 failures remain in enterprise
benchmark tooling (4), logging (2), quick-search (6), SearchAPI (2), Semantic
Scholar (1), Serper (2), source-aware config (1) and WebSocket module import (1).
The focused regression passes the relevant benchmark/config tests in isolation;
the full suite retains the known module/mock pollution. No unrelated tests were
modified. Logs remain ignored under `outputs/batch8-regression.log` and
`outputs/batch8-full-suite-final.log`.

## Independent Review / Repair

Independent read-only review checked the real path and all integration contracts.
Two separate repair workers addressed concrete findings:

1. Legacy result EvaluationAdapter must receive unknown repair count (`None`) when
   there is no structured execution. Added a compatibility test. The unsupported
   provisional trace stage was also replaced by the existing report stage.
2. Windows text newline conversion changed final artifact bytes after hashing.
   Switched final report to UTF-8 byte writes and tested the actual artifact hash.

Final independent review: **PASS**, no remaining deterministic blocker. The reviewer
independently ran the 24 integration/compatibility tests (24 passed, 3 warnings)
and inspected the final test-only registry isolation. No independent reviewer
changed frozen components.

## Frozen Contract Check

Batch 2 ranking/scorer and classifier, Claim/binder, Gate, Grounding, Evaluation,
Trace, architecture/benchmark 2.2 and frozen dataset were not edited. Dataset SHA-256:
`95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`.
V1 branch and commit remain unchanged. No live V1 rerun, annotations or benchmark
results were modified.

## Files Changed

- `backend/server/enterprise_api.py`
- `gpt_researcher/enterprise/workflow.py`
- `gpt_researcher/enterprise/integration.py`
- `gpt_researcher/skills/writer.py`
- `tests/test_enterprise_integration.py`
- `tests/test_batch8_evaluation_compat.py`
- `docs/v2/BATCH8_LOCAL_SMOKE.md`
- `docs/v2/BATCH8_DELIVERY.md`

## Scope Check

New orchestration framework, evaluator, database, dashboard, policy system or
unlimited loop: **NO**. All core algorithm/rule contracts are reused.

## Remaining Issues

None for Batch 8. The inherited full-suite failures and compileall example issue
are outside this batch. Real-provider smoke and semantic usefulness remain
unmeasured; neither is represented as a measured benchmark success.
