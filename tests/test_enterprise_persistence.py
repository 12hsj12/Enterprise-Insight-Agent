import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.server.enterprise_api import create_enterprise_router
from backend.server.report_store import ReportStore
from backend.server.sqlite_report_store import SQLiteReportStore
from gpt_researcher.enterprise import IntelligenceWorkflow
from gpt_researcher.prompts import PromptFamily
from gpt_researcher.skills.context_manager import ContextManager


async def test_sqlite_concurrent_connections_and_restart(tmp_path):
    path = tmp_path / "tasks.db"
    a, b = SQLiteReportStore(path), SQLiteReportStore(path)
    await asyncio.gather(*[(a if i % 2 else b).upsert_report(str(i), {"index": i}) for i in range(24)])
    reopened = SQLiteReportStore(path)
    assert len(await reopened.list_reports()) == 24
    assert await reopened.get_report("5") == {"index": 5}
    assert await reopened.list_reports(["5", "missing"]) == [{"index": 5}]
    await reopened.upsert_report("5", {"index": 99})
    assert await a.get_report("5") == {"index": 99}
    assert await a.delete_report("5") is True
    assert await a.delete_report("5") is False


async def test_recovery_retains_partial_diagnostics(tmp_path):
    store = SQLiteReportStore(tmp_path / "tasks.db")
    await store.upsert_report("running", {"status": "running", "diagnostics": {"search_calls": 2}})
    await store.upsert_report("done", {"status": "completed"})
    assert await store.recover_running() == 1
    interrupted = await store.get_report("running")
    assert interrupted["status"] == "interrupted"
    assert interrupted["diagnostics"]["search_calls"] == 2
    assert (await store.get_report("done"))["status"] == "completed"
    assert await store.recover_running() == 0


async def test_json_corruption_is_not_overwritten(tmp_path):
    path = tmp_path / "old.json"
    original = "{broken JSON"
    path.write_text(original)
    store = ReportStore(path)
    with pytest.raises(ValueError):
        await store.upsert_report("new", {"report": "would lose old data"})
    assert path.read_text() == original


def test_unavailable_store_returns_503_without_research(tmp_path):
    path = tmp_path / "corrupt.sqlite3"
    path.write_text("not a database")
    app = FastAPI()
    app.include_router(create_enterprise_router(SQLiteReportStore(path)))
    with TestClient(app) as client:
        assert client.get("/api/enterprise/health").status_code == 200
        assert client.get("/api/enterprise/ready").status_code == 503
        assert client.post("/api/enterprise/tasks", json={"target": "fixture"}).status_code == 503


class LocalResearcher:
    """Exercises actual ContextManager, compression, evidence and reliability without providers."""
    def __init__(self, **kwargs):
        self.verbose = False
        self.query = kwargs["query"]
        self.cfg = SimpleNamespace(source_reliability_weight=0.0, similarity_threshold=0.42)
        self.memory = SimpleNamespace(get_embeddings=lambda: None)
        self.prompt_family = PromptFamily
        self.kwargs = {}
        self.evidences, self.assessments = [], []
    def add_evidences(self, values): self.evidences.extend(values)
    def add_evidence_assessments(self, values): self.assessments.extend(values)
    def add_costs(self, value): pass
    def get_costs(self): return 0.0
    def get_evidences(self): return self.evidences
    def get_evidence_assessments(self): return self.assessments
    async def conduct_research(self):
        await ContextManager(self).get_similar_content_by_query(self.query, [{
            "url": "https://example.com/product", "title": "Fixture",
            "raw_content": "FixtureCo sells widgets. This is synthetic data."}])
    async def write_report(self, **kwargs):
        return "FixtureCo sells [widgets](https://example.com/product). Synthetic demonstration."


def test_api_workflow_rag_sqlite_end_to_end(tmp_path):
    path = tmp_path / "tasks.db"
    def make_app():
        app = FastAPI()
        app.include_router(create_enterprise_router(SQLiteReportStore(path),
            lambda: IntelligenceWorkflow(LocalResearcher)))
        return app
    with TestClient(make_app()) as client:
        response = client.post("/api/enterprise/tasks", json={"target": "FixtureCo"})
        assert response.status_code == 200
        task = response.json()
        assert task["result"]["evidences"][0]["url"] == "https://example.com/product"
        assert task["diagnostics"]["retrieval_calls"] == 1
        assert task["result"]["assessments"][0]["authority_score"] == 0.6
    with TestClient(make_app()) as client:
        assert client.get("/api/enterprise/tasks/" + task["task_id"]).json() == task
