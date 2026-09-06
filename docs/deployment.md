# Local deployment

Enterprise Insight Agent v1 is a portfolio local deployment on top of GPT Researcher.
Use one application worker: startup marks previously running tasks interrupted. It does
not recover an execution stack or automatically replay provider calls.

## Windows / Python 3.11

Install the repository's existing dependencies in `.venv` and provide your usual
provider/search settings in a local `.env`. Never commit that file. For the frozen
Hugging Face benchmark also install the existing optional integrations
`langchain-huggingface` and `sentence-transformers`, and cache the documented model.

```powershell
.venv/Scripts/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
Invoke-RestMethod http://127.0.0.1:8000/api/enterprise/health
Invoke-RestMethod http://127.0.0.1:8000/api/enterprise/ready
```

`health` checks the application. `ready` opens the local SQLite store and checks access;
neither makes paid calls or guarantees provider availability. The default store is
`outputs/enterprise_tasks.sqlite3`. Set `ENTERPRISE_STORE_PATH` to change it,
`ENTERPRISE_CONFIG_PATH` to select normal GPT Researcher JSON configuration, and
`ENTERPRISE_TASK_TIMEOUT` for the positive task timeout in seconds (default 900).

POST `/api/enterprise/tasks` executes synchronously and returns a structured task record.
GET `/api/enterprise/tasks/{uuid}` retrieves persisted evidence, report and diagnostics;
GET `/api/enterprise/tasks` lists local history. The existing UI/report/chat routes remain
available. A failed request returns a safe task record (502 provider/research failure,
504 timeout, 500 internal invariant). Validation uses 422; missing tasks use 404;
unavailable storage uses 503. A storage failure after generation can leave the previous
running record; startup then marks it interrupted. There is no automatic paid retry.

Timeout cancellation cannot stop a blocking network request already running in a worker
thread. Provider-level timeout and retry behavior still applies. Trace search counts cover
ResearchConductor web searches, not planning searches, MCP or internal provider retries.

## Docker

The root `Dockerfile` is the supported build, using Python 3.11, non-root runtime,
Chromium and PDF system libraries. The legacy backend-only Dockerfile is not this run path.
The minimal Compose configuration uses the existing app without a separate frontend build.

```powershell
docker compose -f docker-compose.enterprise.yml config --quiet
docker compose -f docker-compose.enterprise.yml build
docker compose -f docker-compose.enterprise.yml up -d
Invoke-RestMethod http://127.0.0.1:8000/api/enterprise/ready
docker compose -f docker-compose.enterprise.yml ps
docker compose -f docker-compose.enterprise.yml stop
```

Compose injects `.env` at runtime and binds only localhost. `.dockerignore` excludes
credentials, virtual environments, private notes, generated runs and local databases.
`outputs/` and `logs/` are mounted for persistence. On Linux, ensure their ownership
permits the container's non-root user to write. Runtime configuration must choose an
installed embedding provider; the frozen Hugging Face benchmark is validated separately
in the local Python environment rather than included in the default image.

Dependency ranges follow the upstream project; this is not a fully locked/hermetic image.
No authentication or multi-tenant isolation was added. Keep this deployment local; shared
network operation needs access controls, storage policy and task resource limits.
