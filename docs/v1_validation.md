# Enterprise Insight Agent v1 validation

This file records what was executed, not expected performance. Benchmark cutoff remains
2026-09-05. Live runs began on 2026-09-06 UTC and continued into September 7 local time.
Raw timestamps in each manifest are authoritative.

## Checkpoint tests

All listed commands use `.venv/Scripts/python -m pytest`, with `GPTR_BLOCK_NETWORK=1`,
`-q --tb=short`. Test paths are relative to the repository root.

| Checkpoint | Files / scope | Exact result |
|---|---|---|
| Day 7 | `test_source_aware`, `test_source_aware_config`, `test_evidence_reliability`, `test_evidence_consistency`, `test_context_compressor_source_url`, `test_research_conductor_retrieval`, `test_quick_search_summary_context` | 34 passed, 2 warnings |
| Day 8 | Day 7 scope without quick-search summary, plus `test_enterprise_workflow` | 40 passed, 2 warnings |
| Day 9 | `test_enterprise_evaluation`, `test_enterprise_workflow`, source-aware/config, reliability/consistency, provenance | 44 passed, 2 warnings |
| Day 10 | Day 9 scope plus `test_enterprise_trace`, `test_research_conductor_retrieval` | 50 passed, 2 warnings |
| Day 11 | Day 9 scope plus trace/API and `backend/test_report_chat_route_uniqueness` | 54 passed, 3 warnings |
| Day 12 | Day 11 scope plus `test_enterprise_persistence` | 59 passed, 3 warnings |
| Day 13 setup | Day 12 scope with MCP dedupe replacing backend chat module | 59 passed, 3 warnings |
| Final follow-up | Workflow, evaluation, API, persistence, scraper guards | 26 passed, 3 warnings |
| Final RAG follow-up | Source-aware/config, provenance, reliability/consistency, persistence | 37 passed, 3 warnings |
| Day 14 final regression | All enterprise modules, source-aware/config, reliability/consistency, provenance, backend chat, MCP dedupe and scraper guards | 66 passed, 3 warnings |

Names in the table are `tests/<name>.py` unless a subdirectory is shown. Exact raw
commands and checkpoint commit history are also retained in the ignored local progress
log `my-docs/CODEX_PROGRESS.md`.

Final regression command:

```powershell
$env:GPTR_BLOCK_NETWORK="1"
.venv/Scripts/python -m pytest tests/test_enterprise_evaluation.py tests/test_enterprise_workflow.py tests/test_enterprise_trace.py tests/test_enterprise_api.py tests/test_enterprise_persistence.py tests/test_source_aware.py tests/test_source_aware_config.py tests/test_evidence_reliability.py tests/test_evidence_consistency.py tests/test_context_compressor_source_url.py tests/backend/test_report_chat_route_uniqueness.py tests/skills/test_tavily_mcp_dedupe.py tests/test_scraper_run_guards.py -q --tb=short
```

## Broadest practical offline run

```powershell
.venv/Scripts/python scripts/run_offline_tests.py --output outputs/day13-isolated-final --workers 4
```

**464 passed, 2 skipped, 0 failed, 0 collection errors across 122 modules.**
Machine-readable evidence: `outputs/day13-isolated-final/summary.json`, per-module JUnit
files and raw output. The final run includes empty-report rejection and both normal-config
and legacy-kwarg source-weight regressions.

As in the existing CI, the live modules `test_researcher_logging.py`,
`test_logging_output.py` and `test_mcp.py` are excluded from the offline run. The two
collection skips are `tests/backend/test_write_md_to_pdf_filename.py` and
`tests/test_security_fix.py`: the first requires unavailable native WeasyPrint libraries;
the second already skips because it targets security helper APIs removed upstream.
That legacy security-test coverage gap remains technical debt; this goal did not add a skip.

An earlier monolithic run produced **17 failed, 444 passed, 2 skipped, 4 deselected**.
The repository CI already documented global module-state pollution and used Linux
`--forked`. The portable runner isolates modules on Windows without changing assertions.
Its first run had **459 passed, 2 failed, 2 skipped**; the remaining failures came from
a scraper test's obsolete fake package. Replacing that loader with the actual package
fixed both while preserving the content-filtering assertions. The legacy MCP dedupe
mock was likewise updated to the existing `EvidenceContext` contract.

Warnings include the inherited `asyncio_fixture_loop_scope` pytest setting, a
langchain-community deprecation, and the installed Starlette TestClient/httpx deprecation.
No dependency was added merely to silence warnings.

## Compilation and local demonstration

```powershell
.venv/Scripts/python -m compileall -q gpt_researcher backend/server benchmarks scripts
.venv/Scripts/python -m gpt_researcher.enterprise.demo --output outputs/day14-enterprise-demo.json
```

Both passed. The synthetic demo produced 2 evidence items, matching assessments,
`insufficient` consistency and zero provider calls. Its trace and serialized output
were checked. The cached `all-MiniLM-L6-v2` embedding model generated a 384-dimensional
vector in a local-only preflight.

Expanding compilation to all of `backend/` finds a pre-existing Python 3.11 f-string
syntax error in `backend/report_type/deep_research/example.py:291`. The file is unchanged
from the Day 6 reference and is not imported by the validated application startup path.
This legacy standalone example remains technical debt; a broad compileall is not claimed
to pass. Core application/package, server, benchmark and script compilation does pass.

## Deployment evidence

- `docker compose -f docker-compose.enterprise.yml config --quiet`: passed.
- Docker engine initially unavailable; the installed Docker Desktop engine was started.
- `docker compose -f docker-compose.enterprise.yml build`: passed.
- Built image configuration digest:
  `sha256:03157398bf820701214bf9910db89b4c4ce43f76812f21f973276c05c9856d4d`.
- `up -d --no-build`: passed; container reached `healthy`.
- Container-exposed `/api/enterprise/health` and `/ready`: HTTP 200; OpenAPI includes all
  4 enterprise paths / 5 operations.
- Container UID is 1000. `.env`, `.venv` and the private roadmap were absent from the image.
- SQLite reopen and running-to-interrupted recovery passed inside the container.
- Separate local Uvicorn on port 8765 returned HTTP 200 for health, readiness and task
  listing, then shut down cleanly.

The image was subsequently rebuilt with final runtime hardening and the demo:
`sha256:d5cf50f4c458c3330798823b47a062e82b46bd1b6d59794242b18784a7e50c16`.
The replaced container reached `healthy` again, and the synthetic demo ran inside it
with 2 evidence items and zero provider calls. This is not a paid research execution
inside Docker, a multi-worker test, or a fully locked dependency build.
The validation container was stopped afterward; mounted results and task history were retained.

## Measured development comparison

Both variants ran at `9004478dc52b4ccdca4cc9bb03c6d86c3e6d1624`, using
`benchmarks/configs/baseline.json` and `source_aware.json`. Model settings were
`openai:deepseek-v4-flash` for fast/smart/strategic roles, Hugging Face
`sentence-transformers/all-MiniLM-L6-v2`, Tavily with 5 results/query, similarity threshold
0.42, compression threshold 8000, and source weights 0 / 0.2. Manifests record additional
settings, package versions, dataset hash and timestamps. Credentials are not included.

| Metric: 8 development cases per variant | Baseline w=0 | Source-aware w=0.2 |
|---|---:|---:|
| Completed / attempted | 8 / 8 | 8 / 8 |
| Task failure rate | 0% | 0% |
| Mean observed latency, seconds | 250.0845368625 | 231.5821663125 |
| Total estimated cost, USD | 4.20498034 | 3.89534760 |
| Sum of per-case distinct source counts | 118 | 111 |
| Instrumented web search calls | 32 | 32 |
| Quality-reviewed cases | 0 | 0 |
| Evidence Coverage | null | null |
| Citation Correctness | null | null |
| Citation Completeness | null | null |
| Unsupported Claim Rate | null | null |

Per-case source/search counts and report hashes are in
`benchmarks/results/v1/development/*/results.json`. Raw reports, sources, contexts,
evidence and traces remain in ignored `outputs/day13-*-dev` directories. Curated JSON
artifacts were checked against actual configured credential values before committing.

## Final reserved holdout

Executed once per variant, with the same revision/settings and no holdout tuning:

```powershell
.venv/Scripts/python -m benchmarks.run --variant baseline --split holdout --live --output outputs/day13-baseline-holdout
.venv/Scripts/python -m benchmarks.run --variant source_aware --split holdout --live --output outputs/day13-source-aware-holdout
.venv/Scripts/python -m benchmarks.compare --baseline outputs/day13-baseline-holdout --source-aware outputs/day13-source-aware-holdout --output outputs/day13-holdout-comparison.json
```

| Metric: 4 holdout cases per variant | Baseline w=0 | Source-aware w=0.2 |
|---|---:|---:|
| Completed / attempted | 4 / 4 | 4 / 4 |
| Task failure rate | 0% | 0% |
| Mean observed latency, seconds | 270.3586391750 | 259.5955462750 |
| Total estimated cost, USD | 2.20439738 | 2.13402480 |
| Sum of per-case distinct source counts | 64 | 57 |
| Instrumented web search calls | 16 | 16 |
| Quality-reviewed cases | 0 | 0 |
| All four quality metrics | null | null |

All **24 live attempts** (development plus holdout, both variants) completed. Instrumented
web search failures were zero. Total recorded provider-estimated cost was **$12.43875012**.
These are observed task-execution results, not a claim of factual accuracy. Source counts
are summed per case, not deduplicated across the whole experiment. Search counts exclude
planning/MCP and retries inside providers. Holdout variants overlapped in wall-clock time.

Curated holdout artifacts are under `benchmarks/results/v1/holdout/`; full raw artifacts
remain in the corresponding ignored output directories. Failed attempts would remain in
the denominator; none occurred in these runs. The benchmark dataset is unchanged from
the Day 6 reference.

## Interpretation and remaining limitations

The source-aware weight is an unchanged candidate, not an optimized setting. Runs overlap
one another and other local workloads, and live web/model output is nondeterministic.
Observed latency/cost differences are **not evidence of a causal improvement**. Existing
cost tracking yields provider estimates rather than reconciled invoices.

Quality formulas and annotation validation are implemented and tested. Actual quality
scores require reviewed required-fact, claim and citation annotations tied to each report
hash. Those annotations were not supplied or completed in these runs, so quality is
unmeasured, not zero and not automatically inferred. No accuracy/citation-quality gain
is claimed. The historical EI_001 upstream baseline is a separate experiment.

To complete quality measurement, supply the reviewed annotation JSON specified by
`benchmarks.metrics.QualityAnnotation`, then run, for example:

```powershell
.venv/Scripts/python -m benchmarks.score --run-dir outputs/day13-baseline-holdout --annotations baseline-holdout-annotations.json --output outputs/baseline-holdout-scored
```

The missing input is the reviewed fact/claim/citation labels, not credentials or fabricated
placeholder scores. The same procedure applies to the other three run directories.
