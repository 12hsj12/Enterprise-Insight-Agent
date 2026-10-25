"""Attach reviewed annotations to a new scored artifact without editing raw runs."""

import argparse
import json
from pathlib import Path

from benchmarks.metrics import QualityAnnotation, quality_metrics, summarize
from benchmarks.run import digest, write_json


def score_run(run_dir: Path, annotations_path: Path, output: Path):
    records = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    annotations = [QualityAnnotation.model_validate(a) for a in json.loads(annotations_path.read_text(encoding="utf-8"))]
    by_id = {a.run_id: a for a in annotations}
    if len(by_id) != len(annotations) or set(by_id) - {r["run_id"] for r in records}:
        raise ValueError("Duplicate or unknown annotated run IDs")
    for record in records:
        annotation = by_id.get(record["run_id"])
        if annotation is None:
            continue
        if record["status"] != "completed":
            raise ValueError("Cannot score an uncompleted run")
        report = (run_dir / record["case_id"] / "report.md").read_text(encoding="utf-8")
        if digest(report) != annotation.report_sha256 or annotation.report_sha256 != record["report_sha256"]:
            raise ValueError("Annotation report hash mismatch")
        record.update(quality_metrics(annotation))
        record["quality_annotation"] = annotation.model_dump()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "manifest.json", json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")))
    write_json(output / "results.json", records)
    write_json(output / "summary.json", summarize(records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    score_run(args.run_dir, args.annotations, args.output)
