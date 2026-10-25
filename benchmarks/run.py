"""Run frozen cases: python -m benchmarks.run --variant baseline --split development.

Default is a non-billable dry run. Live mode executes every selected case once,
retains failures, and never scores report quality without reviewed annotations.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from benchmarks.metrics import quality_metrics, summarize
from gpt_researcher.enterprise.trace import RunTrace

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "benchmarks/dataset/enterprise_insight_bench_v0.json"
VARIANTS = ("baseline", "source_aware")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cases(split: str) -> tuple[dict, list[dict]]:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data["cases"]
    if len(cases) != 12 or len({c["id"] for c in cases}) != 12:
        raise ValueError("Expected 12 unique frozen cases")
    if sum(c["split"] == "development" for c in cases) != 8:
        raise ValueError("Expected 8 development cases")
    if any(c["cutoff_date"] != "2026-09-05" for c in cases):
        raise ValueError("Benchmark cutoff changed")
    selected = [c for c in cases if c["split"] == split]
    if len(selected) != (8 if split == "development" else 4):
        raise ValueError("Unexpected split")
    return data, selected


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


async def run_benchmark(variant: str, split: str, output: Path, live: bool = False,
                        researcher_factory=None, timeout_s: float = 900) -> dict:
    if variant not in VARIANTS:
        raise ValueError("Unknown benchmark variant")
    data, cases = load_cases(split)
    config_path = ROOT / f"benchmarks/configs/{variant}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    # Environment overrides are legitimate in the app, but not silently in a controlled experiment.
    from gpt_researcher.config import Config
    effective = Config(str(config_path))
    if any(getattr(effective, key.lower()) != value for key, value in config.items()):
        raise ValueError("Environment overrides frozen benchmark configuration; clear conflicting variables")
    if os.getenv("COMPRESSION_THRESHOLD", "8000") != "8000":
        raise ValueError("COMPRESSION_THRESHOLD must remain 8000")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "experiment_id": str(uuid4()), "variant": variant, "split": split,
        "mode": "live" if live else "dry_run", "commit_sha": git_sha(),
        "created_at": datetime.now(timezone.utc).isoformat(), "config": config,
        "effective_settings": {key: getattr(effective, key.lower()) for key in (
            "CURATE_SOURCES", "TEMPERATURE", "SCRAPER", "MAX_SCRAPER_WORKERS",
            "REASONING_EFFORT", "MCP_STRATEGY", "IMAGE_GENERATION_ENABLED",
            "FAST_TOKEN_LIMIT", "SMART_TOKEN_LIMIT", "STRATEGIC_TOKEN_LIMIT",
        )},
        "compression_threshold": 8000,
        "max_content_chars": int(os.getenv("MAX_CONTENT_CHARS", "50000")),
        "python_version": sys.version.split()[0],
        "package_versions": {name: importlib.metadata.version(name) for name in (
            "langchain-core", "langchain-classic", "pydantic", "openai",
        )},
        "dataset_sha256": digest(DATASET.read_text(encoding="utf-8")),
        "cutoff_date": data["cutoff_date"], "timeout_s": timeout_s,
        "comparison": "Same-version zero-weight ablation, not a rerun of the historical upstream baseline",
    }
    write_json(output / "manifest.json", manifest)
    records = []
    if live and researcher_factory is None:
        from gpt_researcher import GPTResearcher
        researcher_factory = GPTResearcher
    for case in cases:
        record = {
            "run_id": f"{manifest['experiment_id']}_{case['id']}", "case_id": case["id"],
            "variant": variant, "status": "dry_run", "latency_s": None,
            "estimated_cost_usd": None, "source_count": None, "search_calls": None,
            "quality_annotation": None, **quality_metrics(None),
        }
        case_dir = output / case["id"]
        case_dir.mkdir()
        write_json(case_dir / "input.json", case)
        if live:
            researcher = None
            trace = RunTrace(record["run_id"])
            started = time.perf_counter()
            try:
                researcher = researcher_factory(
                    query=case["query"] + f"\nInformation cutoff: {case['cutoff_date']}. Exclude later developments.",
                    config_path=str(config_path), report_type="research_report", report_source="web", verbose=False,
                )
                async def execute():
                    with trace.activate():
                        with trace.stage("research"):
                            context = await researcher.conduct_research()
                        with trace.stage("report"):
                            report = await researcher.write_report()
                    return context, report
                context, report = await asyncio.wait_for(execute(), timeout_s)
                if not report.strip():
                    raise ValueError("Empty report")
                (case_dir / "report.md").write_text(report, encoding="utf-8")
                write_json(case_dir / "context.json", context)
                evidences = researcher.get_evidences()
                write_json(case_dir / "evidence.json", [e.model_dump(mode="json") for e in evidences])
                sources = researcher.get_research_sources()
                write_json(case_dir / "sources.json", sources)
                record.update(status="completed", report_sha256=digest(report),
                              source_count=len({s.get("url") for s in sources if s.get("url")}))
            except Exception as exc:
                # Provider error messages can contain credentials or signed request URLs.
                record.update(status="failed", error_type=type(exc).__name__)
            finally:
                record["latency_s"] = time.perf_counter() - started
                record["search_calls"] = trace.search_calls
                record["search_failures"] = trace.search_failures
                write_json(case_dir / "trace.json", trace.snapshot())
                if researcher is not None:
                    record["estimated_cost_usd"] = researcher.get_costs()
        records.append(record)
        write_json(case_dir / "metrics.json", record)
        write_json(output / "results.json", records)
    summary = summarize(records)
    write_json(output / "summary.json", summary)
    return summary


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--split", choices=["development", "holdout"], default="development")
    parser.add_argument("--live", action="store_true", help="Execute paid provider/search calls")
    parser.add_argument("--output", type=Path, required=True, help="New output directory (never overwrite runs)")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_benchmark(args.variant, args.split, args.output, args.live)), indent=2))


if __name__ == "__main__":
    main()
