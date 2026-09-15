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


def validate_manifest(case_ids):
    """Reject a malformed Batch 5 manifest before any live capability is used."""
    if len(case_ids) != len(IDS):
        raise ValueError(f"Batch 5 requires exactly {len(IDS)} cases")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Batch 5 manifest contains duplicate case IDs")
    if tuple(case_ids) != IDS:
        raise ValueError("Batch 5 manifest must use the frozen development case order")


def effective_payload(request):
    """Return the exact POST payload after validating the required V2 mode."""
    if not request.enable_v2_execution:
        raise ValueError("Batch 5 requires enable_v2_execution=true")
    if not request.enable_v2_evidence_selection:
        raise ValueError("Batch 5 requires enable_v2_evidence_selection=true")
    payload = request.model_dump(mode="json")
    if payload.get("enable_v2_execution") is not True:
        raise ValueError("Batch 5 execution flag was not propagated into the request payload")
    if payload.get("enable_v2_evidence_selection") is not True:
        raise ValueError("Batch 5 evidence-selection flag was not propagated into the request payload")
    return payload


def iter_manifest_requests(cases):
    """Yield each validated future live request exactly once in manifest order."""
    validate_manifest([case["id"] for case, _ in cases])
    for case, request in cases:
        yield case, effective_payload(request)


def preflight(case_ids=IDS):
    from gpt_researcher.enterprise.workflow import IntelligenceRequest
    assert sha256((ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json").read_bytes()) == DATASET_SHA
    validate_manifest(case_ids)
    cases = []
    for cid in case_ids:
        paths = list(PACKAGE.glob(f"*/{cid}/case_input.json"))
        assert len(paths) == 1
        case = json.loads(paths[0].read_text(encoding="utf-8"))
        assert case["id"] == cid and case["split"] == "development"
        assert case["cutoff_date"] == "2026-09-05"
        # Preserve full query; no gold category or rule injected into classifier.
        request = IntelligenceRequest(target=case["query"], topic="Development research",
            cutoff_date=case["cutoff_date"], dimensions=[u["description"] for u in case["required_units"]],
            enable_v2_execution=True, enable_v2_evidence_selection=True)
        cases.append((case, request))
    assert sum(len(c[0]["required_units"]) for c in cases) == 18
    # Validate final serialized values, not merely constructor arguments.
    list(iter_manifest_requests(cases))
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
        for case, payload in iter_manifest_requests(cases):
            cid = case["id"]
            print(f"START {cid}", flush=True)
            capture = CalibrationCapture()
            with capture.activate():
                response = await client.post("/api/enterprise/tasks", json=payload)
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
        payloads = list(iter_manifest_requests(preflight()))
        print(json.dumps({
            "status": "PREFLIGHT_OK",
            "provider_calls": 0,
            "search_calls": 0,
            "development_live_runs": 0,
            "holdout_live_runs": 0,
            "case_sequence": [case["id"] for case, _ in payloads],
            "effective_v2_config": {
                "enable_v2_execution": payloads[0][1]["enable_v2_execution"],
                "enable_v2_evidence_selection": payloads[0][1]["enable_v2_evidence_selection"],
            },
        }, ensure_ascii=False))
