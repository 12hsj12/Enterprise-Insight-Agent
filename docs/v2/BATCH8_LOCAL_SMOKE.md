# Batch 8 local execution

Run from the repository root on `feat/evidence-v2`, using the existing Python
3.11 `.venv` and existing local server. This is a manual provider-dependent smoke
path, not a benchmark run. No live calls are required by the integration tests.

## Provider configuration

For the default configuration, provide `OPENAI_API_KEY` (LLM and OpenAI embeddings)
and `TAVILY_API_KEY` (search) in your local environment or uncommitted `.env`.
Use account-supported `FAST_LLM`, `SMART_LLM`, `STRATEGIC_LLM` and `EMBEDDING`
settings. The existing defaults use OpenAI; compatible providers may additionally
require `OPENAI_BASE_URL`. `ENTERPRISE_CONFIG_PATH` selects an existing GPT
Researcher JSON config. Do not use frozen benchmark configurations as smoke data.
The readiness endpoint checks local persistence, not provider credentials.

```powershell
.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

In a second PowerShell terminal at the repository root:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/enterprise/ready
$smokeBody = @{
    target = 'Microsoft'
    topic = 'Verify the business purpose of Azure OpenAI Service'
    cutoff_date = '2026-09-05'
    dimensions = @('Supported findings', 'Evidence limitations')
    enable_v2_execution = $true
} | ConvertTo-Json -Depth 20
$smokeTask = Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8000/api/enterprise/tasks `
    -ContentType 'application/json' -Body $smokeBody
$smokeTask.task_id
$smokeTask.result.output_artifact_reference
$smokeTask.result.trace_artifact_reference
$smokeTask.evaluation_result
Invoke-RestMethod "http://127.0.0.1:8000/api/enterprise/tasks/$($smokeTask.task_id)"
```

POST is synchronous and can take several minutes. It invokes paid provider APIs.
The existing `ENTERPRISE_TASK_TIMEOUT` defaults to 900 seconds. The existing
provider utility has bounded transport retries (up to 10 for non-streaming calls);
Batch 8 adds no model retry or retrieval continuation loop. A malformed structured
authoring response fails the run rather than being repaired by another LLM call.

## Representative smoke requests

Use the same POST command, changing only the target/topic. These examples are
separate from the frozen benchmark and do not modify its labels or Required Units.

| Intent | Target | Topic |
|---|---|---|
| Factual verification | Microsoft | Verify the business purpose of Azure OpenAI Service |
| Competitive comparison | Microsoft and Amazon | Compare Azure OpenAI Service and Amazon Bedrock capabilities and identify evidence gaps |
| Conflict-sensitive intelligence | Microsoft and Amazon | Investigate conflicting claims about enterprise AI service capabilities; distinguish source assertions and unresolved disagreements |

Inspect the returned classification; these are manual requests, not gold category
labels or accuracy measurements. High-risk assertions without explicit source
qualifications may be omitted. A report containing only a stated evidence
limitation is a valid abstention, not proof of useful coverage or benchmark success.

## Artifacts and evaluation

- `outputs/enterprise/<task_id>/report.md`: final deterministic Markdown only.
- `outputs/enterprise/<task_id>/execution.json`: selected Evidence, registered
  Claims, explicit links, claim-scoped qualifications/context, persisted Gate
  obligations, final generated citation subsets, pre/post grounding and repair
  plan; report SHA-256 and run/trace identifiers. No duplicate report body.
- `outputs/enterprise/traces/<trace_id>.json`: one existing typed research trace;
  contains observations rather than source/report text.
- Existing task history (`outputs/enterprise_tasks.sqlite3` by default) and
  GET task response: result, actual artifact references, and `evaluation_result`.
  No new database or storage engine is introduced.

The API uses task ID as the evaluation case ID for manual runs. Python callers
can call `result.to_evaluation_case(case_id)` with their independently established
case identity. This invokes Batch 6 `EvaluationAdapter`; it does not calculate
benchmark correctness/Required Unit annotations or Baseline metrics. Unavailable
qualification/reliability aggregates remain null. Claim-scoped qualifications
remain in `execution.claim_inputs`, never promoted to global qualifications.

Failed API tasks expose a bounded error code, failed evaluation result and the
failed trace reference when export succeeded. They have no successful result or
final output reference. Trace export is fail-open and its reference is null when
unavailable. Core artifact export fails the workflow; a partially written audit
or `.pending` file is not a successful report. Run directories are never reused.

## Structured authoring and explicit qualifications

Without `claim_plan`, the existing ReportGenerator uses its researcher's configured
provider to author one bounded JSON proposal (at most 60 atomic claims). The writer
supplies text, frozen risk labels, materiality, explicit support/conflict/unclear
relations and the chosen citation subset. The adapter constructs stable Claim IDs
before binding any relation. These are authoring inputs, not independently reviewed
semantic entailment results; inaccurate labels or relations remain a limitation.

The original Batch 8 writer could not supply qualifications. The subsequent
Qualification Coverage Integration now lets the same single structured authoring
call provide bounded entity/side references, claim/evidence associations, and
content-anchored source identity candidates. Deterministic validation maps only
accepted inputs into the existing `ClaimEvidenceQualification`; missing or invalid
metadata remains unqualified. For explicit reviewed inputs, the same API accepts
optional `claim_plan` using `ClaimPlan` in OpenAPI:
each `items[]` contains an existing `Claim`, `links`, claim-specific
`qualifications`, `gate_context`, and `cited_evidence_ids`; optional `audit_metadata`
supplies observed publication dates. Omit `claim_id` within Claim to let the existing
model calculate it, but links must reference that stable ID. All evidence IDs must
match evidence actually selected in this execution. Stale/unmatched input fails;
there is no URL-based ID remapping or URL/authority/ranking-based qualification.

The fixture tests exercise qualified numeric, conflict-side HEDGE, missing metadata,
unknown IDs, citation-subset repair and failure cases without real provider keys.
Normal browser/WebSocket free-text report routes retain their existing behavior;
use this Enterprise API with `enable_v2_execution=true` for the gated V2 path.

```powershell
$env:GPTR_BLOCK_NETWORK = '1'
.venv/Scripts/python.exe -m pytest tests/test_enterprise_integration.py tests/test_batch8_evaluation_compat.py -q
```
