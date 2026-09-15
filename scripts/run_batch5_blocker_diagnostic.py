"""One authorized development case through the real local enterprise POST route.

The output is diagnostic evidence only; it is never benchmark scoring input.
"""

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_development_calibration import ROOT, preflight, effective_payload, write
from gpt_researcher.enterprise.report_diagnostics import ReportDiagnosticCapture


async def execute(case_id: str, output: Path):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import os
    import httpx
    from fastapi import FastAPI
    from backend.server.enterprise_api import create_enterprise_router
    from backend.server.report_store import ReportStore
    from gpt_researcher.enterprise.workflow import IntelligenceWorkflow

    cases = dict((case["id"], (case, request)) for case, request in preflight())
    case, request = cases[case_id]
    payload = effective_payload(request)
    for key in ("OPENAI_API_KEY", "TAVILY_API_KEY"):
        if not os.getenv(key):
            raise RuntimeError("Required credential unavailable: " + key)
    output.mkdir(parents=True, exist_ok=False)
    app = FastAPI()
    app.include_router(create_enterprise_router(
        ReportStore(output / "task_store.json"),
        workflow_factory=lambda: IntelligenceWorkflow(output_directory=output / "enterprise"),
    ))
    capture = ReportDiagnosticCapture()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://diagnostic.local", timeout=None) as client:
        with capture.activate():
            response = await client.post("/api/enterprise/tasks", json=payload)
    task = response.json()
    write(output / "task.json", task)
    capture.export(output / "report_diagnostic.json")
    write(output / "run.json", {
        "case_id": case_id, "split": case["split"],
        "task_id": task.get("task_id"), "status": task.get("status"),
        "http_status": response.status_code,
        "report_artifact": (task.get("result") or {}).get("output_artifact_reference"),
        "diagnostic_artifact": str(output / "report_diagnostic.json"),
        "benchmark_scoring": False, "holdout_calls": 0,
    })
    print(json.dumps({"case_id": case_id, "status": task.get("status"),
                      "http_status": response.status_code,
                      "diagnostic": str(output / "report_diagnostic.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("EIV2_TC_001", "EIV2_CC_001"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(execute(args.case, args.output.resolve()))
