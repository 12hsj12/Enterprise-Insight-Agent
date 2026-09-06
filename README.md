# Enterprise Insight Agent v1

An evidence-centric competitive-intelligence application built by extending **GPT Researcher**.
It preserves source provenance, applies an optional source reliability prior after semantic
retrieval, and exposes inspectable reports through a typed API with local task history.

This is a portfolio-grade local reference implementation. Its three engineering pillars
are **Evidence Reliability**, **Source-aware RAG & Context Engineering**, and
**Evaluation + Observability**. Competitive intelligence is the business workflow that uses them.

## Why extend GPT Researcher?

GPT Researcher already provides planning, search, scraping, compression and report generation.
For enterprise analysis, a cited report alone is insufficient: an analyst also needs the
underlying evidence, an explanation of source selection, visible uncertainty, reproducible
experiments, and retrievable task history. This project extends the existing pipeline rather
than replacing it with a second agent stack.

## Implemented capabilities

| Area | Behavior |
|---|---|
| Evidence reliability | Separate raw evidence, source-prior assessments, explicit claim links and consistency assessments |
| Source-aware RAG | Normal JSON/environment configuration; reranking after semantic filtering; zero-weight baseline preserved |
| Competitive intelligence | Typed company/topic/cutoff request; structured provenance alongside a generated report |
| Evaluation | Frozen 12 cases (8 dev / 4 holdout), reproducible manifests/raw outputs, retained failures, hash-bound reviewed metrics |
| Observability | Optional bounded traces with stage timing, scoped search counts and selected evidence scores |
| API and persistence | Execute/list/get tasks, health/readiness, SQLite history and interrupted-task recovery |
| Deployment | Python 3.11 local path and a non-root Docker image with a readiness health check |

The ranking rule is:

```text
final_score = (1 - w) * similarity_score + w * authority_score
```

`SOURCE_RELIABILITY_WEIGHT=0.0` is the default. The measured candidate uses `0.2`; it is
not an optimized value. Authority is a **source-level reliability prior**, not factual
correctness or claim confidence. Consistency is not fact checking. See the
[architecture and data flow](docs/enterprise_architecture.md).

## Quickstart

From this repository on Windows / Python 3.11:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r multi_agents/requirements.txt
.venv/Scripts/python -m gpt_researcher.enterprise.demo --output outputs/enterprise-demo.json
```

The last command is a credential-free **synthetic** demonstration through the actual
compression/evidence/workflow code. It is not a research benchmark.

For real research, create a local `.env` with `OPENAI_API_KEY` and `TAVILY_API_KEY`.
For an OpenAI-compatible provider, also configure `OPENAI_BASE_URL` and supported
`FAST_LLM`, `SMART_LLM` and `STRATEGIC_LLM` values. Never commit credentials. Use an
installed embedding provider; the benchmark's Hugging Face setup additionally needs
`langchain-huggingface`, `sentence-transformers` and the cached model.

```powershell
.venv/Scripts/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
# In another terminal:
Invoke-RestMethod http://127.0.0.1:8000/api/enterprise/ready
```

Open `http://127.0.0.1:8000/docs` for the API. Follow the [demo request/retrieval flow](docs/demo.md)
and [deployment guide](docs/deployment.md). Real tasks call paid providers when configured.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/enterprise/health` | Application liveness |
| GET | `/api/enterprise/ready` | Local store readiness; no provider probe |
| POST | `/api/enterprise/tasks` | Synchronously execute a typed intelligence request |
| GET | `/api/enterprise/tasks` | List persisted local history |
| GET | `/api/enterprise/tasks/{uuid}` | Retrieve report, evidence and diagnostics |

Existing GPT Researcher report, chat, WebSocket and UI routes remain available.

## Docker

```powershell
docker compose -f docker-compose.enterprise.yml config --quiet
docker compose -f docker-compose.enterprise.yml up -d --build
Invoke-RestMethod http://127.0.0.1:8000/api/enterprise/ready
```

Compose loads `.env` at runtime and binds localhost. Outputs and logs persist in mounted
local directories. The image excludes `.env`, virtual environments, generated runs and
private notes. Use one worker for startup recovery. Build, startup, health checks and a
container SQLite recovery smoke test were actually exercised; details are in the
[validation report](docs/v1_validation.md).

## Evaluation

The cutoff remains **2026-09-05**. Both variants use the same frozen case/query/model/
retriever settings, with source weight 0 versus 0.2. This is a same-version ablation,
not a rerun of the historical upstream baseline.

| Development set (8 cases) | Weight 0 | Weight 0.2 |
|---|---:|---:|
| Completed / attempted | 8 / 8 | 8 / 8 |
| Task failures | 0 | 0 |
| Mean observed latency | 250.08 s | 231.58 s |
| Total provider-estimated cost | $4.20498034 | $3.89534760 |
| Four evidence/citation quality metrics | Unreviewed | Unreviewed |

| Reserved holdout (4 cases) | Weight 0 | Weight 0.2 |
|---|---:|---:|
| Completed / attempted | 4 / 4 | 4 / 4 |
| Task failures | 0 | 0 |
| Mean observed latency | 270.36 s | 259.60 s |
| Total provider-estimated cost | $2.20439738 | $2.13402480 |
| Four evidence/citation quality metrics | Unreviewed | Unreviewed |

These values are real runs at `9004478d`; [curated manifests/results](benchmarks/results/v1/)
include per-case hashes, costs, counts and failures. Runs overlapped other local work, and
live search/model output varies. **No controlled latency, cost or quality improvement is claimed.**
Quality metrics remain null pending reviewed annotations rather than being inferred from
URL counts. Final holdout results and limitations are recorded in the validation report.

```powershell
# Non-billable dry run; choose a fresh output directory.
.venv/Scripts/python -m benchmarks.run --variant baseline --split development --output outputs/baseline-dry
# Add --live for actual provider calls; reserve --split holdout for final evaluation.
```

See [benchmark execution and scoring](benchmarks/README.md) and the
[original metric definitions](docs/baseline_protocol.md).

## Tests

```powershell
.venv/Scripts/python -m pip install pytest pytest-asyncio pytest-timeout
$env:GPTR_BLOCK_NETWORK="1"
.venv/Scripts/python -m pytest tests/test_enterprise_workflow.py tests/test_enterprise_api.py tests/test_enterprise_persistence.py tests/test_source_aware.py -q
# Windows-compatible process isolation for the broad offline suite:
.venv/Scripts/python scripts/run_offline_tests.py --output outputs/offline-tests --workers 4
```

The isolation runner preserves CI's three live-module exclusions and every test assertion.
It exists because inherited tests mutate global module state; a monolithic process is not
a reliable regression signal. Exact commands, counts and remaining warnings appear in
[validation](docs/v1_validation.md).

## Limitations and next work

- Reviewed claim/citation annotations are still required to measure research quality.
- Date cutoff is a research instruction, not a verified publication-date filter.
- Structured evidence coverage is currently strongest on the web compression path; MCP
  and vector-store paths can still contribute context without evidence objects.
- Source rules are incomplete and official sources may be biased. Freshness is not scored.
- Requests are synchronous; cancellation cannot forcibly stop every blocking provider call.
- SQLite history/restart marking is not a durable task queue. No distributed execution,
  multi-tenant authorization or production access-control system was added.
- Dependencies follow upstream ranges; builds are not fully hermetic. Local cost estimates
  are not reconciled with provider invoices.

Next priorities are a reviewed evaluation corpus, broader provenance coverage, dated-source
validation and controlled paired retrieval experiments. See [resume and interview notes](docs/career.md)
for an engineering explanation grounded in what is implemented.

## Attribution

Built on [GPT Researcher](https://github.com/assafelovic/gpt-researcher). Existing planning,
search, scraping, writing and UI functionality are reused; enterprise-specific changes are
in this repository's feature history. See [LICENSE](LICENSE) for repository license terms.
