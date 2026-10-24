# Enterprise Insight Agent

**Evidence-grounded enterprise research for competitive intelligence and related decision tasks.** This product builds on the research and writing foundations of [GPT Researcher](https://github.com/assafelovic/gpt-researcher).

[English](README.md) · [简体中文](README-zh_CN.md)

> Evidence reliability controls how strongly a claim is stated; it does not decide whether information is present.

## Project positioning

Enterprise Insight Agent is a local reference implementation for research that must show how findings are supported, where sources disagree, and which recommendation premises remain uncertain. Its product flow combines research planning, web retrieval, evidence assessment, claim review, citation grounding, and an inspectable report record.

The codebase retains GPT Researcher's research and writing foundations. The project attribution and applicable license are described in [License and attribution](#license-and-attribution).

## Technical architecture

```text
Research request
  → planning, search, scraping, and context compression
  → semantic eligibility and task-aware source reranking
  → structured EvidenceContext with provenance and diagnostics
  → report draft and answer-critical claim review
  → claim/evidence binding, qualification, Claim Gate, and citation grounding
  → bounded local repair, final report, trace, and evaluation record
```

The writer drafts from the research context before the evidence audit. The audit reviews claims in that draft; audit-generated claims absent from it are discarded. `Evidence`, source-level `EvidenceAssessment`, cross-source `EvidenceConsistencyAssessment`, and `ClaimEvidenceLink` are separate records. `authority_score` is a source reliability prior, not a probability that a claim is true. Task classification selects the authority weight after semantic eligibility; other `EvidencePolicy` fields are guidance and are not all enforced as retrieval filters. See the [architecture specification](docs/v2/V2_ARCHITECTURE_SPEC.md) and [information-flow note](docs/v2/INFORMATION_FLOW_SIMPLIFICATION.md).

## Core modules

| Module | Responsibility |
|---|---|
| `gpt_researcher/skills/researcher.py`, `gpt_researcher/context/` | Research planning, retrieval, compression, source-aware context, and provenance. |
| `gpt_researcher/evidence/` | Evidence records, metadata, reliability priors, claim binding, consistency, qualification, and grounding. |
| `gpt_researcher/enterprise/` | Request workflow, task policy, answer-critical review, report diagnostics, trace, and structured results. |
| `backend/server/enterprise_api.py`, `backend/server/sqlite_report_store.py` | Local enterprise task API and SQLite task history. |
| `benchmarks/`, `tests/`, `scripts/run_offline_tests.py` | Frozen evaluation inputs and outputs, regression coverage, and module-isolated offline test runner. |

## Run

The project targets Python 3.11 or later. Dependency files specify minimum versions rather than a fully locked environment; the Docker build uses the same requirements files. From the repository root on Windows:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r multi_agents/requirements.txt
.venv/Scripts/python -m gpt_researcher.enterprise.demo --output outputs/enterprise-demo.json
```

The demo uses synthetic fixture data and makes no provider calls. It demonstrates software behavior; it is not a live research run or benchmark.

For a real research request, configure working LLM, embedding, and search providers in an uncommitted local `.env` (the default setup uses `OPENAI_API_KEY` and `TAVILY_API_KEY`) and start the API:

```powershell
.venv/Scripts/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

Submit an enterprise research task from another PowerShell terminal. Provider calls may incur cost:

The local API currently exposes the evidence workflow through the `enable_v2_execution` request field.

```powershell
$body = @{
    target = 'Microsoft'
    topic = 'Verify the business purpose of Azure OpenAI Service'
    dimensions = @('Supported findings', 'Evidence limitations')
    enable_v2_execution = $true
} | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/enterprise/tasks -ContentType 'application/json' -Body $body
```

The request runs synchronously. Open `http://127.0.0.1:8000/docs` for the API. The [deployment guide](docs/deployment.md) and [request walkthrough](docs/demo.md) cover local operation and persistence.

## Tests and evaluation

Install the test extra with `python -m pip install -e ".[test]"`, then run the module-isolated offline suite with a new output directory:

```powershell
.venv/Scripts/python scripts/run_offline_tests.py --output outputs/offline-run --workers 4
```

The runner sets `GPTR_BLOCK_NETWORK=1` and excludes the three provider/live modules `test_researcher_logging.py`, `test_logging_output.py`, and `test_mcp.py`. Choose a different output directory for each run.

The frozen benchmark specification defines 30 cases in six categories: 18 development cases and 12 reserved holdout cases, with a 2026-09-05 information cutoff. A one-pass run of the 12 holdout cases completed **12/12 with zero case-level runtime failures and zero quality reruns**. Human review of the saved reports rated product generalization **MIXED**: engineering stability passed, evidence-aware behavior was mixed, and readability was acceptable. This completion count is not a report-quality score, and no paired quantitative comparison has established an improvement over the upstream project. See the [benchmark specification](docs/v2/V2_BENCHMARK_SPEC.md) and [holdout evaluation](docs/v2/V2_HOLDOUT_ONE_PASS_EVALUATION.md) for methods and detailed results.

## Known limitations

- First-party sources, independent corroboration, publication dates, and comparable competitor evidence may be unavailable. A source reliability prior cannot fill those gaps.
- Complex comparisons, trend analysis, and recommendations can rely on weak or incompatible evidence. The holdout review found conclusions and recommendation premises requiring source-level human review before enterprise use.
- The 2026-09-05 information cutoff was not reliably enforced in all generated content; post-cutoff source metadata appeared in holdout reports. Long reports can repeat qualification language and be difficult to scan.
- The frozen quantitative acceptance criteria remain unevaluated without a complete formal metric ledger and paired comparison. Runtime counters are diagnostics, not accuracy scores.
- The local API uses synchronous execution and SQLite history. It has no authentication, multi-tenant isolation, durable distributed queue, or distributed job coordination.

## License and attribution

This repository is built on [GPT Researcher](https://github.com/assafelovic/gpt-researcher), whose research and writing foundations are retained and extended as one product. The repository's license is [Apache License 2.0](LICENSE); retain applicable upstream notices and consult the upstream repository for its own terms. The Python distribution keeps the `gpt-researcher` package identifier for compatibility.

## Documentation map

- [Documentation home](docs/docs/welcome.md)
- [Architecture specification](docs/v2/V2_ARCHITECTURE_SPEC.md) · [Frozen benchmark specification](docs/v2/V2_BENCHMARK_SPEC.md) · [Holdout evaluation](docs/v2/V2_HOLDOUT_ONE_PASS_EVALUATION.md)
- [Baseline benchmark protocol](docs/baseline_protocol.md) · [Validation log](docs/v1_validation.md)
- [License](LICENSE) · [Contribution guide](CONTRIBUTING.md)
