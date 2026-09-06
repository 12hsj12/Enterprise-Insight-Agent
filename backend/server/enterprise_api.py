"""Typed local enterprise API, independent of existing UI report routes."""

import asyncio
from datetime import datetime, timezone
from typing import Callable, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gpt_researcher.enterprise import IntelligenceRequest, IntelligenceResult, IntelligenceWorkflow
from gpt_researcher.enterprise.trace import RunTrace


class TaskRecord(BaseModel):
    task_id: str
    status: Literal["running", "completed", "failed", "interrupted"]
    created_at: datetime
    updated_at: datetime
    request: IntelligenceRequest
    result: IntelligenceResult | None = None
    error_code: str | None = None
    diagnostics: dict | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "ready"]
    service: str = "Enterprise Insight Agent"
    provider_check: str = "not_checked"


def create_enterprise_router(store, workflow_factory: Callable = IntelligenceWorkflow,
                             timeout_s: float = 900) -> APIRouter:
    if timeout_s <= 0:
        raise ValueError("Enterprise timeout must be positive")
    router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])

    @router.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="ok")

    @router.get("/ready", response_model=HealthResponse)
    async def ready():
        try:
            if hasattr(store, "check_health"):
                await store.check_health()
            else:
                await store.list_reports()
        except (OSError, ValueError):
            raise HTTPException(503, "Task store unavailable") from None
        return HealthResponse(status="ready")

    @router.get("/tasks", response_model=list[TaskRecord])
    async def list_tasks():
        try:
            records = await store.list_reports()
        except (OSError, ValueError):
            raise HTTPException(503, "Task store unavailable") from None
        return [TaskRecord.model_validate(record) for record in records]

    @router.get("/tasks/{task_id}", response_model=TaskRecord)
    async def get_task(task_id: UUID):
        try:
            record = await store.get_report(str(task_id))
        except (OSError, ValueError):
            raise HTTPException(503, "Task store unavailable") from None
        if record is None:
            raise HTTPException(404, "Task not found")
        return TaskRecord.model_validate(record)

    @router.post("/tasks", response_model=TaskRecord,
                 responses={500: {"model": TaskRecord}, 502: {"model": TaskRecord}, 504: {"model": TaskRecord}})
    async def execute_task(request: IntelligenceRequest):
        task_id = str(uuid4())
        now = datetime.now(timezone.utc)
        task = TaskRecord(task_id=task_id, status="running", created_at=now, updated_at=now, request=request)
        trace = RunTrace(task_id)
        try:
            await store.upsert_report(task_id, task.model_dump(mode="json"))
        except (OSError, ValueError):
            raise HTTPException(503, "Task store unavailable") from None
        status_code = 200
        try:
            task.result = await asyncio.wait_for(
                workflow_factory().run(request, run_id=task_id, trace=trace), timeout_s)
            task.status = "completed"
        except asyncio.CancelledError:
            task.status, task.error_code = "interrupted", "request_cancelled"
            task.updated_at = datetime.now(timezone.utc)
            task.diagnostics = trace.snapshot()
            await asyncio.shield(store.upsert_report(task_id, task.model_dump(mode="json")))
            raise
        except TimeoutError:
            task.status, task.error_code, status_code = "failed", "research_timeout", 504
        except (ValueError, TypeError, AssertionError):
            task.status, task.error_code, status_code = "failed", "internal_invariant", 500
        except Exception:
            task.status, task.error_code, status_code = "failed", "research_failed", 502
        task.updated_at = datetime.now(timezone.utc)
        task.diagnostics = trace.snapshot()
        try:
            await store.upsert_report(task_id, task.model_dump(mode="json"))
        except (OSError, ValueError):
            raise HTTPException(503, "Task result could not be persisted") from None
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=task.model_dump(mode="json"))
        return task

    return router
