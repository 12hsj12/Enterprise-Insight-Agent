"""Read-only, offline verification of the populated local calibration package."""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/v2/calibration/v2.2.0"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    def reject(value):
        raise ValueError("Non-finite JSON value")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def verify():
    manifest = read(PACKAGE / "CALIBRATION_MANIFEST.json")
    assert digest(ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json") == manifest["dataset_sha256"]
    assert manifest["dataset_sha256"] == "95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa"
    assert manifest["human_review_status"] == "PENDING" and manifest["reviewer"] is None
    ledger = read(PACKAGE / "FULL_AI_ASSISTED_LEDGER.json")
    queue = read(PACKAGE / "HUMAN_REVIEW_QUEUE.json")
    core = read(PACKAGE / "HUMAN_CALIBRATION_CORE.json")["tasks"]
    adjudication = read(PACKAGE / "HUMAN_ADJUDICATION_QUEUE.json")["tasks"]
    items = ledger["items"]
    assert ledger["status"] == "AI_ASSISTED" and not ledger["final_gold"]
    assert len(items) == ledger["item_count"] == 483 == len({i["review_id"] for i in items})
    assert len(core) == manifest["human_calibration_core_item_count"]
    assert len(adjudication) == manifest["human_adjudication_queue_item_count"]
    assert len(core) + len(adjudication) == manifest["human_review_item_count"] == queue["after_human_workload_count"]
    ledger_ids = {item["review_id"] for item in items}
    ledger_by_id = {item["review_id"]: item for item in items}
    human_tasks = core + adjudication
    assert all(set(task["ledger_review_ids"]) <= ledger_ids for task in human_tasks)
    for task in human_tasks:
        linked = [ledger_by_id[review_id] for review_id in task["ledger_review_ids"]]
        assert {item["case_id"] for item in linked} == {task["case_id"]}
        assert {item["category"] for item in linked} == {task["category"]}
        for human_field in ("reviewer_identity", "human_decision", "review_timestamp", "adjudication_note"):
            assert task[human_field] is None
    hashes = selected_count = 0
    scan_paths = set(p for p in PACKAGE.rglob("*") if p.is_file())
    for case in manifest["cases"]:
        directory = PACKAGE / case["category"] / case["case_id"]
        for ref in case["artifacts"].values():
            original = ROOT / ref["original_runtime_path"]
            assert digest(original) == ref["original_runtime_sha256"]
            if ref["path"].endswith(("execution.json", "trace.json")):
                assert read(original) == read(ROOT / ref["path"])
            scan_paths.add(original)
        for name, expected in read(directory / "hashes.json").items():
            path = ROOT / name
            assert digest(path) == expected, name
            scan_paths.add(path)
            hashes += 1
        meta = read(directory / "case_input.json")
        assert meta["split"] == "development" and meta["id"] == case["case_id"]
        report = (directory / "report.md").read_text(encoding="utf-8")
        execution = read(directory / "execution.json")
        assert execution["run_id"] == case["task_id"]
        assert execution["trace_id"] == case["trace_id"] == read(directory / "trace.json")["trace_id"]
        assert digest(directory / "report.md") == execution["execution"]["report_sha256"]
        selected = read(directory / "selected.json")["evidences"]
        candidate = read(ROOT / case["artifacts"]["candidate"]["path"])
        for evidence in selected:
            assert any(e["sub_query"] == evidence["sub_query"] and
                       p.get("source", p.get("url")) == evidence["url"] and p["content"] == evidence["content"]
                       for e in candidate["events"] if e["stage"] == "eligible_chunks_before_ranking"
                       for p in e["records"])
            selected_count += 1
        case_items = [i for i in items if i["case_id"] == case["case_id"]]
        assert {i["required_unit_id"] for i in case_items if i["item_type"] == "required_unit"} == {u["id"] for u in meta["required_units"]}
        by_id = {e["evidence_id"]: e for e in selected}
        for item in case_items:
            for name in ("reviewer_identity", "human_decision", "review_timestamp", "adjudication_note"):
                assert item[name] is None
            assert "FINAL_LABEL" not in item and "final_label" not in item
            if item.get("exact_report_text"):
                start, end = item["report_span"]
                assert report[start:end] == item["exact_report_text"]
            for saved in item["saved_evidence"]:
                evidence = by_id[saved["evidence_id"]]
                assert saved["exact_saved_evidence_excerpt"] == evidence["content"]
                assert saved["source_reference"] == evidence["url"]
        records = execution["execution"]["evidence_context"]["generated_claim_records"]
        assert {i["runtime_claim_id"] for i in case_items if i["item_type"] == "claim_segmentation"} == {r["claim_id"] for r in records}
        for task in [task for task in human_tasks if task["case_id"] == case["case_id"]]:
            passage = task.get("exact_report_passage") or task.get("material", {}).get("exact_report_passage")
            if passage:
                assert passage in report
            task_evidence = task.get("evidence") or task.get("material", {}).get("evidence", [])
            linked_evidence = {
                saved["evidence_id"]: saved
                for review_id in task["ledger_review_ids"]
                for saved in ledger_by_id[review_id].get("saved_evidence", [])
            }
            for saved in task_evidence:
                assert saved["evidence_id"] in linked_evidence
                assert saved["source_reference"] == linked_evidence[saved["evidence_id"]]["source_reference"]
                assert saved["excerpt_location"] == linked_evidence[saved["evidence_id"]]["excerpt_location"]
    # Scan actual configured secret values without printing or serializing them.
    from dotenv import dotenv_values
    environment = {**dotenv_values(ROOT / ".env"), **os.environ}
    secrets = [v.encode("utf-8") for k, v in environment.items() if isinstance(v, str) and len(v) >= 8
               and re.search(r"key|token|secret|password|credential", k, re.I)]
    for path in scan_paths:
        data = path.read_bytes()
        assert not any(secret in data for secret in secrets), "Configured secret in " + str(path.relative_to(ROOT))
        if path.suffix == ".json":
            read(path)
    result = {"status": "PASSED", "verified_artifact_hashes": hashes, "selected_candidate_matches": selected_count,
              "full_ledger_items": len(items), "human_review_items": len(human_tasks), "required_units": 18, "configured_secret_matches": 0,
              "finite_utf8_json": True, "official_holdout_executions": 0}
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    verify()
