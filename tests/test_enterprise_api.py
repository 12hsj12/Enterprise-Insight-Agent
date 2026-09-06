import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.server.enterprise_api import create_enterprise_router
from backend.server.report_store import ReportStore
from gpt_researcher.enterprise import IntelligenceResult
from gpt_researcher.evidence import EvidenceConsistencyAssessment


class FakeWorkflow:
    async def run(self, request, run_id, trace):
        with trace.stage("research"):
            pass
        return IntelligenceResult(run_id=run_id, request=request, report="Fixture report",
            evidences=[], assessments=[], consistency=EvidenceConsistencyAssessment(status="insufficient"), source_urls=[])


def client(tmp_path, workflow=FakeWorkflow, timeout=30):
    app = FastAPI()
    app.include_router(create_enterprise_router(ReportStore(tmp_path / "tasks.json"), workflow, timeout))
    return TestClient(app)


def test_execute_retrieve_and_health(tmp_path):
    with client(tmp_path) as api:
        assert api.get("/api/enterprise/health").status_code == 200
        assert api.get("/api/enterprise/ready").json()["provider_check"] == "not_checked"
        response = api.post("/api/enterprise/tasks", json={"target": "FixtureCo"})
        assert response.status_code == 200
        task = response.json()
        assert task["status"] == "completed"
        assert task["diagnostics"]["run_id"] == task["task_id"]
        assert api.get("/api/enterprise/tasks/" + task["task_id"]).json() == task
        assert len(api.get("/api/enterprise/tasks").json()) == 1


def test_validation_and_not_found(tmp_path):
    with client(tmp_path) as api:
        for body in ({"target": " "}, {"target": "a", "dimensions": [""]}, {"target": "a", "headers": {}}):
            assert api.post("/api/enterprise/tasks", json=body).status_code == 422
        assert api.get("/api/enterprise/tasks/invalid").status_code == 422
        assert api.get("/api/enterprise/tasks/00000000-0000-0000-0000-000000000000").status_code == 404


def test_failure_persists_safe_diagnostics(tmp_path):
    class Broken:
        async def run(self, request, run_id, trace):
            with trace.stage("research"):
                raise ConnectionError("secret-token")
    with client(tmp_path, Broken) as api:
        response = api.post("/api/enterprise/tasks", json={"target": "FixtureCo"})
        assert response.status_code == 502
        assert "secret-token" not in response.text
        task = response.json()
        assert task["error_code"] == "research_failed"
        assert api.get("/api/enterprise/tasks/" + task["task_id"]).json()["status"] == "failed"


def test_timeout_and_invariant_status(tmp_path):
    class Slow:
        async def run(self, request, **kwargs):
            await asyncio.sleep(1)
    with client(tmp_path, Slow, 0.01) as api:
        assert api.post("/api/enterprise/tasks", json={"target": "FixtureCo"}).status_code == 504
    class Invalid:
        async def run(self, request, **kwargs):
            raise ValueError("broken internal evidence IDs")
    with client(tmp_path, Invalid) as api:
        assert api.post("/api/enterprise/tasks", json={"target": "FixtureCo"}).status_code == 500
