"""Six fixed development requests through the real enterprise POST route.

HTTP uses ASGI transport in-process; workflow/research/providers are real. This
operator-invoked adapter has no ablation, replay, holdout or quality retry support.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gpt_researcher.enterprise.calibration_capture import CalibrationCapture, canonical_bytes, sha256, scrub

IDS = ("EIV2_FV_001", "EIV2_TC_001", "EIV2_CC_001", "EIV2_TM_003", "EIV2_CR_003", "EIV2_ED_002")
DATASET_SHA = "95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa"
PACKAGE = ROOT / "docs/v2/calibration/v2.2.0"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    def safe(item):
        if isinstance(item, str):
            return scrub(item)
        if isinstance(item, dict):
            return {key: safe(val) for key, val in item.items()}
        if isinstance(item, list):
            return [safe(val) for val in item]
        return item
    path.write_bytes(canonical_bytes(safe(value)))


def preflight():
    from gpt_researcher.enterprise.workflow import IntelligenceRequest
    assert sha256((ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json").read_bytes()) == DATASET_SHA
    cases = []
    for cid in IDS:
        paths = list(PACKAGE.glob(f"*/{cid}/case_input.json"))
        assert len(paths) == 1
        case = json.loads(paths[0].read_text(encoding="utf-8"))
        assert case["id"] == cid and case["split"] == "development"
        assert case["cutoff_date"] == "2026-09-05"
        # Preserve full query; no gold category or rule injected into classifier.
        request = IntelligenceRequest(target=case["query"], topic="Development research",
            cutoff_date=case["cutoff_date"], dimensions=[u["description"] for u in case["required_units"]],
            enable_v2_execution=True)
        cases.append((case, request))
    assert sum(len(c[0]["required_units"]) for c in cases) == 18
    return cases


async def execute(output):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import os
    from fastapi import FastAPI
    import httpx
    from backend.server.enterprise_api import create_enterprise_router
    from backend.server.report_store import ReportStore
    from gpt_researcher.enterprise.workflow import IntelligenceWorkflow
    cases = preflight()
    for key in ("OPENAI_API_KEY", "TAVILY_API_KEY"):
        if not os.getenv(key):
            raise RuntimeError("Required credential unavailable: " + key)
    output.mkdir(parents=True, exist_ok=False)
    app = FastAPI()
    app.include_router(create_enterprise_router(ReportStore(output / "task_store.json"),
        workflow_factory=lambda: IntelligenceWorkflow(output_directory=output / "enterprise")))
    config = {key: os.getenv(key) for key in ("FAST_LLM", "SMART_LLM", "STRATEGIC_LLM", "EMBEDDING")}
    config.update(search="TavilySearch", transport="httpx.ASGITransport (real POST router; in-process)")
    write(output / "configuration.json", config)
    summaries = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://calibration.local", timeout=None) as client:
        for case, request in cases:
            cid = case["id"]
            print(f"START {cid}", flush=True)
            capture = CalibrationCapture()
            with capture.activate():
                response = await client.post("/api/enterprise/tasks", json=request.model_dump(mode="json"))
            task = response.json()
            directory = output / cid
            write(directory / "task.json", task)
            write(directory / "candidate.json", {"case_id": cid, "task_id": task.get("task_id"),
                "boundary": "pages before compression and eligible chunks before ranking; NOT paired replay",
                "events": capture.events, "capture_errors": capture.errors})
            result = task.get("result") or {}
            write(directory / "selected.json", {"case_id": cid, "task_id": task.get("task_id"),
                "evidences": result.get("evidences", [])})
            write(directory / "scoring.json", {"case_id": cid, "assessments": result.get("assessments", []),
                "retrieval_diagnostics": result.get("retrieval_diagnostics", []),
                "task_classification": result.get("task_classification"), "evidence_policy": result.get("evidence_policy"),
                "note": "Existing runtime scores only; candidate similarities in candidate.json; no new scores."})
            summary = {"case_id": cid, "category": case["category"], "task_id": task.get("task_id"),
                "status": task.get("status"), "http_status": response.status_code,
                "created_at": task.get("created_at"), "updated_at": task.get("updated_at"),
                "trace_id": task.get("trace_id"), "trace": task.get("trace_artifact_reference"),
                "report": result.get("output_artifact_reference"), "execution": result.get("execution_artifact_reference"),
                "cost_usd_runtime_estimate": result.get("estimated_cost_usd"), "capture_errors": capture.errors}
            summaries.append(summary)
            write(output / "runs.json", summaries)
            print(f"END {cid} {task.get('status')} {task.get('task_id')}", flush=True)
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Authorized paid six-case development execution")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    preflight()
    if args.execute:
        if args.output is None:
            parser.error("--output required for append-only live execution")
        asyncio.run(execute(args.output.resolve()))
    else:
        print("PREFLIGHT_OK six development cases / 18 Required Units / dataset hash verified; no provider calls")
