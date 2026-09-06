"""Compare compatible raw/scored benchmark artifacts without dropping failures."""

import argparse
import json
from pathlib import Path

from benchmarks.metrics import summarize
from benchmarks.run import load_cases, write_json

QUALITY = ("evidence_coverage", "citation_correctness", "citation_completeness", "unsupported_claim_rate")


def compare_runs(baseline: Path, source_aware: Path) -> dict:
    def load(path, name):
        return json.loads((path / name).read_text(encoding="utf-8"))
    a, b = load(baseline, "manifest.json"), load(source_aware, "manifest.json")
    for key in ("split", "dataset_sha256", "cutoff_date", "effective_settings", "compression_threshold", "max_content_chars",
                "commit_sha", "python_version", "package_versions", "timeout_s"):
        if a.get(key) != b.get(key):
            raise ValueError(f"Incompatible experiment field: {key}")
    if a["mode"] != "live" or b["mode"] != "live":
        raise ValueError("Dry runs are not measured comparisons")
    if a["variant"] != "baseline" or b["variant"] != "source_aware":
        raise ValueError("Expected baseline and source_aware variants")
    ac, bc = a["config"].copy(), b["config"].copy()
    if ac.pop("SOURCE_RELIABILITY_WEIGHT") != 0:
        raise ValueError("Baseline must have zero weight")
    if not 0 < bc.pop("SOURCE_RELIABILITY_WEIGHT") <= 1:
        raise ValueError("Source-aware weight must be positive and at most one")
    if ac != bc:
        raise ValueError("Controlled configurations differ beyond source weight")
    ar, br = load(baseline, "results.json"), load(source_aware, "results.json")
    if {r["case_id"] for r in ar} != {r["case_id"] for r in br}:
        raise ValueError("Comparison requires the same cases including failures")
    expected = 8 if a["split"] == "development" else 4
    if len(ar) != expected or len(br) != expected:
        raise ValueError("Incomplete benchmark split")
    expected_ids = {case["id"] for case in load_cases(a["split"])[1]}
    for records in (ar, br):
        if {r["case_id"] for r in records} != expected_ids:
            raise ValueError("Missing or duplicate frozen cases")
        if any(r["status"] not in ("completed", "failed") for r in records):
            raise ValueError("Comparison requires terminal measured attempts")
    def aggregate(records):
        result = summarize(records)
        costs = [r["estimated_cost_usd"] for r in records]
        result["total_estimated_cost_usd"] = sum(costs) if all(c is not None for c in costs) else None
        result["cost_known_cases"] = sum(c is not None for c in costs)
        # No mean over a favorable subset: every case must have a defined quality metric.
        for key in QUALITY:
            values = [r.get(key) for r in records]
            result[key] = sum(values) / len(values) if all(v is not None for v in values) else None
        return result
    return {"comparison": "same-version weight ablation", "split": a["split"],
            "baseline_commit": a["commit_sha"], "source_aware_commit": b["commit_sha"],
            "baseline": aggregate(ar), "source_aware": aggregate(br),
            "limitations": ["Live web results are not a fixed corpus.",
                            "Latency includes failed attempts and local resource contention.",
                            "Quality means require annotations for every case; null is unavailable."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--source-aware", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    comparison = compare_runs(args.baseline, args.source_aware)
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, comparison)
    print(json.dumps(comparison, indent=2))
