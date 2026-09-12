from collections import Counter
import json
from pathlib import Path
import shutil

import pytest

from scripts.compress_human_review_queue import compress


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/v2/calibration/v2.2.0"


def load(name):
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def test_three_layers_preserve_ledger_and_bound_workload():
    ledger = load("FULL_AI_ASSISTED_LEDGER.json")
    core = load("HUMAN_CALIBRATION_CORE.json")["tasks"]
    adjudication = load("HUMAN_ADJUDICATION_QUEUE.json")["tasks"]
    summary = load("HUMAN_REVIEW_COMPRESSION.json")

    assert ledger["status"] == "AI_ASSISTED"
    assert ledger["final_gold"] is False
    assert len(ledger["items"]) == ledger["item_count"] == 483
    assert len(core) == 51
    assert len(adjudication) == 36
    assert summary["after_human_workload_items"] == 87
    assert summary["machine_resolved_no_human_action_items"] == 227


def test_compression_is_idempotent_and_protects_human_work(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    for filename in (
        "FULL_AI_ASSISTED_LEDGER.json",
        "CALIBRATION_MANIFEST.json",
        "VALIDATION.json",
    ):
        shutil.copy2(PACKAGE / filename, package / filename)
    first = compress(package)
    second = compress(package)
    assert second == first
    core_path = package / "HUMAN_CALIBRATION_CORE.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))
    core["tasks"][0]["human_decision"] = "reviewer-entered-value"
    core_path.write_text(json.dumps(core, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Refusing to overwrite human review work"):
        compress(package)


def test_all_required_units_and_semantic_boundaries_are_covered():
    items = load("FULL_AI_ASSISTED_LEDGER.json")["items"]
    core = load("HUMAN_CALIBRATION_CORE.json")["tasks"]
    adjudication = load("HUMAN_ADJUDICATION_QUEUE.json")["tasks"]
    core_refs = {value for task in core for value in task["ledger_review_ids"]}
    adjudication_refs = {value for task in adjudication for value in task["ledger_review_ids"]}

    required = {item["review_id"] for item in items if item["item_type"] == "required_unit"}
    semantic = {
        item["review_id"]
        for item in items
        if item["ambiguity_flag"]
        and item["item_type"] in {"claim_segmentation", "citation_support", "high_risk"}
    }
    assert len(required) == 18
    assert required <= core_refs
    assert len(semantic) == 203
    assert semantic <= adjudication_refs
    date_boundary_ids = {"EIV2_ED_002-freshness-003"}
    assert date_boundary_ids <= adjudication_refs


def test_calibration_sampling_is_stratified_where_material_exists():
    items = load("FULL_AI_ASSISTED_LEDGER.json")["items"]
    core = load("HUMAN_CALIBRATION_CORE.json")["tasks"]
    sample_counts = Counter((task["category"], task["dimension"]) for task in core)
    for category in {item["category"] for item in items}:
        assert sample_counts[(category, "required_unit")] == 3
        for dimension, limit in {
            "claim_segmentation": 2,
            "citation_support": 2,
            "evidence_strength": 1,
            "independence": 1,
        }.items():
            available = any(
                item["category"] == category
                and item["item_type"] == dimension
                and not item["ambiguity_flag"]
                for item in items
            )
            assert sample_counts[(category, dimension)] == (limit if available else 0)


def test_human_tasks_only_reference_saved_material_and_leave_human_fields_unset():
    ledger = load("FULL_AI_ASSISTED_LEDGER.json")["items"]
    by_id = {item["review_id"]: item for item in ledger}
    tasks = load("HUMAN_CALIBRATION_CORE.json")["tasks"] + load("HUMAN_ADJUDICATION_QUEUE.json")["tasks"]
    for task in tasks:
        assert task["human_review_status"] == "PENDING"
        for field in ("reviewer_identity", "human_decision", "review_timestamp", "adjudication_note"):
            assert task[field] is None
        assert task["ledger_review_ids"]
        assert all(review_id in by_id for review_id in task["ledger_review_ids"])
        assert task.get("exact_report_passage") or task.get("material")
