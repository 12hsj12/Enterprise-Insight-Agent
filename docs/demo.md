# Reproduce the demo

## Offline software demonstration

From the repository root, with the normal Python environment installed:

```powershell
.venv/Scripts/python -m gpt_researcher.enterprise.demo --output outputs/enterprise-demo.json
```

This uses **synthetic FixtureCo data** with a small researcher fixture and runs
the real ContextManager, short-document compression, evidence IDs, reliability evaluator,
workflow contract and trace. It makes no provider calls. The JSON contains two evidence
items, their assessments, a report and stage diagnostics. Consistency remains `insufficient`
because no reviewed claim links were supplied. Choose a new output filename for repeat runs.
It does not exercise the live planner, web scraper or model provider.

The SQLite/API integration is exercised without network access by:

```powershell
$env:GPTR_BLOCK_NETWORK="1"
.venv/Scripts/python -m pytest tests/test_enterprise_persistence.py -q
```

## Real competitive-intelligence task

Start the server using [deployment instructions](deployment.md). Its normal `.env`
must configure a working LLM and search provider; these requests can incur charges.

```powershell
$body = @{
    target = "Xiaomi"
    topic = "Publicly disclosed mobile AI agent capabilities"
    cutoff_date = "2026-09-05"
} | ConvertTo-Json
$task = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/enterprise/tasks -ContentType "application/json" -Body $body
$task.status
$task.result.report
Invoke-RestMethod "http://127.0.0.1:8000/api/enterprise/tasks/$($task.task_id)"
```

The POST waits for completion. The returned task ID addresses the persisted result;
history can also be listed with GET `/api/enterprise/tasks`. Evidence and diagnostics
are embedded in the typed response. OpenAPI is available at `/docs`. Change the company
and topic freely; the production workflow is not hard-coded to the demo company.

In a walkthrough, show the request, the source URLs/evidence IDs, ranking configuration,
the limitations field, and retrieval of the same task after restarting the single worker.
Do not describe the synthetic fixture as a benchmark or claim that source priors verify facts.
