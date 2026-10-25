"""Portable module-isolated offline suite (Windows alternative to pytest --forked).

Keeps CI's three live modules excluded, preserves all assertions, writes each module's
JUnit/output plus an aggregate JSON report. Exit code is nonzero on any failed module.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LIVE = {"test_researcher_logging.py", "test_logging_output.py", "test_mcp.py"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    files = sorted(path for path in (ROOT / "tests").rglob("test_*.py") if path.name not in LIVE)
    env = dict(os.environ, GPTR_BLOCK_NETWORK="1", PYTHONIOENCODING="utf-8")
    def run(path):
        name = str(path.relative_to(ROOT)).replace("\\", "_").replace("/", "_")
        xml = output / (name + ".xml")
        command = [sys.executable, "-m", "pytest", str(path), "-q", "--tb=short", "--timeout=60", f"--junitxml={xml}"]
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=240)
            (output / (name + ".txt")).write_bytes(result.stdout + result.stderr)
            counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
            if xml.exists():
                for suite in ET.parse(xml).getroot().iter("testsuite"):
                    for key in counts:
                        counts[key] += int(suite.attrib.get(key, 0))
            return {"module": str(path.relative_to(ROOT)), "exit_code": result.returncode, **counts}
        except subprocess.TimeoutExpired:
            return {"module": str(path.relative_to(ROOT)), "exit_code": 124, "timeout": True}
    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(run, path) for path in files]):
            record = future.result()
            records.append(record)
            (output / "results.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
            print(f"{len(records)}/{len(files)} {record['module']}: {record['exit_code']}", flush=True)
    counts = {key: sum(r.get(key, 0) for r in records) for key in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    counts["failed_modules"] = [r["module"] for r in records if r["exit_code"] not in (0, 5)]
    counts["excluded_live_modules"] = sorted(LIVE)
    (output / "summary.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    print(json.dumps(counts, indent=2))
    return bool(counts["failed_modules"])


if __name__ == "__main__":
    raise SystemExit(main())
