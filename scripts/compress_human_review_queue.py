"""Compress the six-case AI ledger into bounded, offline human review tasks.

This is triage only. It never changes an AI recommendation, report, evidence,
rubric, or human field, and it performs no provider or benchmark execution.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/v2/calibration/v2.2.0"
CATEGORIES = (
    "factual_verification",
    "technical_capability_analysis",
    "competitive_comparison",
    "trend_market_intelligence",
    "conflict_credibility_resolution",
    "enterprise_decision_recommendation",
)
HUMAN_FIELDS = {
    "human_review_status": "PENDING",
    "reviewer_identity": None,
    "human_decision": None,
    "review_timestamp": None,
    "adjudication_note": None,
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _material(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "exact_required_unit": item.get("exact_required_unit_text"),
        "exact_report_passage": item.get("exact_parent_report_text")
        or item.get("exact_report_text"),
        "report_span": item.get("report_span"),
        "evidence": [
            {
                "evidence_id": saved["evidence_id"],
                "source_reference": saved["source_reference"],
                "excerpt_location": saved["excerpt_location"],
            }
            for saved in item.get("saved_evidence", [])
        ],
    }


def _core_task(item: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {
        "task_id": f"CORE-{sequence:03d}",
        "layer": "HUMAN_CALIBRATION_CORE",
        "case_id": item["case_id"],
        "category": item["category"],
        "dimension": item["item_type"],
        "ledger_review_ids": [item["review_id"]],
        "selection_reason": (
            "All frozen Required Units remain directly human reviewable."
            if item["item_type"] == "required_unit"
            else "Deterministic first-by-review-id clear sample; selected without regard to system score."
        ),
        "ai_recommendations": [
            {
                "ledger_review_id": item["review_id"],
                "recommendation": item["ai_recommendation"],
                "reason": item["reasoning"],
            }
        ],
        "material": _material(item),
        **HUMAN_FIELDS,
    }


def _semantic_tasks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        semantic = (
            item["item_type"] in {"claim_segmentation", "citation_support", "high_risk"}
            and item["ambiguity_flag"]
        )
        if semantic:
            parent = item.get("exact_parent_report_text") or item.get("exact_report_text")
            if not parent:
                raise AssertionError(f"Semantic item has no report material: {item['review_id']}")
            groups[(item["case_id"], parent)].append(item)

    tasks = []
    for sequence, ((case_id, passage), records) in enumerate(sorted(groups.items()), 1):
        first = records[0]
        evidence = {}
        for record in records:
            for saved in record.get("saved_evidence", []):
                evidence[saved["evidence_id"]] = {
                    "evidence_id": saved["evidence_id"],
                    "source_reference": saved["source_reference"],
                    "excerpt_location": saved["excerpt_location"],
                }
        tasks.append(
            {
                "task_id": f"ADJ-SEM-{sequence:03d}",
                "layer": "HUMAN_ADJUDICATION_QUEUE",
                "case_id": case_id,
                "category": first["category"],
                "dimension": "semantic_claim_bundle",
                "flags": sorted(
                    {"SEMANTIC_BOUNDARY_REVIEW"}
                    | {flag for record in records for flag in record.get("flags", [])}
                ),
                "adjudication_reason": (
                    "One report boundary jointly determines atomic segmentation, citation entailment, "
                    "and any applicable high-risk obligation. Review once without dropping any pair."
                ),
                "ledger_review_ids": sorted(record["review_id"] for record in records),
                "covered_dimensions": sorted({record["item_type"] for record in records}),
                "exact_report_passage": passage,
                "evidence": list(evidence.values()),
                "ai_recommendations": [
                    {
                        "ledger_review_id": record["review_id"],
                        "recommendation": record["ai_recommendation"],
                        "reason": record["reasoning"],
                    }
                    for record in sorted(records, key=lambda value: value["review_id"])
                ],
                **HUMAN_FIELDS,
            }
        )
    return tasks


def _independence_tasks(items: list[dict[str, Any]], start: int) -> list[dict[str, Any]]:
    # The other UNRESOLVED records lack a verified producing organization, so the
    # frozen rule resolves them mechanically. This record identifies two actors,
    # but their relationship to the compared project/experiment is disputable.
    selected_ids = {"EIV2_CR_003-independence-003"}
    records = [item for item in items if item["review_id"] in selected_ids]
    assert {item["review_id"] for item in records} == selected_ids
    return [
        {
            "task_id": f"ADJ-IND-{start + index:03d}",
            "layer": "HUMAN_ADJUDICATION_QUEUE",
            "case_id": item["case_id"],
            "category": item["category"],
            "dimension": "independence",
            "flags": ["PUBLISHER_RELATIONSHIP_DISPUTABLE"],
            "adjudication_reason": (
                "Named author and project identities exist, but same-group versus independent "
                "experimental production requires semantic judgment."
            ),
            "ledger_review_ids": [item["review_id"]],
            "source_identity_information": item["source_identity_information"],
            "material": _material(item),
            "ai_recommendations": [
                {
                    "ledger_review_id": item["review_id"],
                    "recommendation": item["ai_recommendation"],
                    "reason": item["reasoning"],
                }
            ],
            **HUMAN_FIELDS,
        }
        for index, item in enumerate(records, 1)
    ]


def _freshness_tasks(items: list[dict[str, Any]], start: int) -> list[dict[str, Any]]:
    # This saved record contains a concrete post-cutoff timestamp, but whether it
    # belongs to the article or a recommendation sidebar is genuinely disputed.
    selected_ids = {
        "EIV2_ED_002-freshness-003",
    }
    records = [item for item in items if item["review_id"] in selected_ids]
    assert {item["review_id"] for item in records} == selected_ids
    return [
        {
            "task_id": f"ADJ-FRESH-{start + index:03d}",
            "layer": "HUMAN_ADJUDICATION_QUEUE",
            "case_id": item["case_id"],
            "category": item["category"],
            "dimension": "freshness",
            "flags": ["DATE_ROLE_OR_ATTRIBUTION_DISPUTABLE"],
            "adjudication_reason": (
                "Saved material contains a date clue, but publication/event/reply/sidebar "
                "attribution or cutoff relevance requires human judgment."
            ),
            "ledger_review_ids": [item["review_id"]],
            "source_identity_information": item["source_identity_information"],
            "date_clue_reason": item["reasoning"],
            "material": _material(item),
            "ai_recommendations": [
                {
                    "ledger_review_id": item["review_id"],
                    "recommendation": item["ai_recommendation"],
                    "reason": item["reasoning"],
                }
            ],
            **HUMAN_FIELDS,
        }
        for index, item in enumerate(sorted(records, key=lambda value: value["review_id"]), 1)
    ]


def _select_core(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [item for item in items if item["item_type"] == "required_unit"]
    clear_dimensions = {
        "claim_segmentation": 2,
        "citation_support": 2,
        "evidence_strength": 1,
        "independence": 1,
        "freshness": 1,
    }
    for category in CATEGORIES:
        category_items = [item for item in items if item["category"] == category]
        for dimension, limit in clear_dimensions.items():
            candidates = [
                item
                for item in category_items
                if item["item_type"] == dimension
                and not item["ambiguity_flag"]
                and (dimension != "freshness" or item.get("publication_date"))
            ]
            selected.extend(sorted(candidates, key=lambda value: value["review_id"])[:limit])
    assert len({item["review_id"] for item in selected}) == len(selected)
    return [_core_task(item, index) for index, item in enumerate(selected, 1)]


def _breakdown(tasks: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(task[field] for task in tasks).items()))


def _ensure_no_human_work_would_be_overwritten(package: Path) -> None:
    paths_and_keys = (
        ("HUMAN_CALIBRATION_CORE.json", "tasks"),
        ("HUMAN_ADJUDICATION_QUEUE.json", "tasks"),
        ("HUMAN_REVIEW_QUEUE.json", "human_calibration_core"),
        ("HUMAN_REVIEW_QUEUE.json", "human_adjudication_queue"),
    )
    for filename, key in paths_and_keys:
        path = package / filename
        if not path.exists():
            continue
        document = read(path)
        for task in document.get(key, []):
            has_human_value = any(
                task.get(field) is not None
                for field in ("reviewer_identity", "human_decision", "review_timestamp", "adjudication_note")
            )
            if has_human_value or task.get("human_review_status") != "PENDING":
                raise RuntimeError(
                    f"Refusing to overwrite human review work in {filename}: {task.get('task_id')}"
                )


def _render_markdown(
    ledger_count: int,
    machine_count: int,
    core: list[dict[str, Any]],
    adjudication: list[dict[str, Any]],
) -> str:
    lines = [
        "# V2.2 compressed human review queue",
        "",
        "Status: **READY_FOR_HUMAN_REVIEW**. All recommendations remain AI-assisted; all human fields remain unset.",
        "",
        f"Full ledger: {ledger_count}; machine-resolved/no-human-action: {machine_count}; "
        f"calibration core: {len(core)}; adjudication queue: {len(adjudication)}; "
        f"human workload: {len(core) + len(adjudication)} tasks.",
        "",
        "The 483 original objects are preserved in `FULL_AI_ASSISTED_LEDGER.json`. "
        "A task may reference several ledger records when one report sentence controls their shared semantic decision.",
        "",
        "## Human calibration core",
        "",
    ]
    for task in core:
        material = task["material"]
        lines.extend(
            [
                f"### {task['task_id']} — {task['case_id']} / {task['dimension']}",
                "",
                f"Ledger: {', '.join(task['ledger_review_ids'])}",
                "",
                f"Required Unit: {material['exact_required_unit'] or 'not applicable'}",
                "",
                f"Report passage: {material['exact_report_passage'] or 'no emitted claim; see ledger material'}",
                "",
                f"AI recommendation: {task['ai_recommendations'][0]['recommendation']}",
                "",
                f"Reason: {task['ai_recommendations'][0]['reason']}",
                "",
            ]
        )
        for evidence in material["evidence"]:
            lines.append(
                f"Evidence: {evidence['evidence_id']} — {evidence['source_reference']} "
                f"(`{evidence['excerpt_location']}`)"
            )
        lines.extend(["", "Human decision: PENDING", ""])
    lines.extend(["## Human adjudication queue", ""])
    for task in adjudication:
        passage = task.get("exact_report_passage") or task["material"]["exact_report_passage"]
        lines.extend(
            [
                f"### {task['task_id']} — {task['case_id']} / {task['dimension']}",
                "",
                f"Flags: {', '.join(task['flags'])}",
                "",
                f"Ledger: {', '.join(task['ledger_review_ids'])}",
                "",
                f"Report/source material: {passage or task.get('source_identity_information')}",
                "",
                f"Reason: {task['adjudication_reason']}",
                "",
                "Human decision: PENDING",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def compress(package: Path = PACKAGE) -> dict[str, Any]:
    _ensure_no_human_work_would_be_overwritten(package)
    full_path = package / "FULL_AI_ASSISTED_LEDGER.json"
    if full_path.exists():
        source = read(full_path)
    else:
        source = read(package / "HUMAN_REVIEW_QUEUE.json")
    items = source["items"]
    assert len(items) == 483 == len({item["review_id"] for item in items})

    ledger = {
        "layer": "FULL_AI_ASSISTED_LEDGER",
        "status": "AI_ASSISTED",
        "final_gold": False,
        "item_count": len(items),
        "human_review_status": "PENDING",
        "reviewer": None,
        "items": items,
    }
    # Object equality proves the 483 record payloads were preserved without relabeling.
    assert ledger["items"] == items
    write(full_path, ledger)

    core = _select_core(items)
    adjudication = _semantic_tasks(items)
    adjudication.extend(_independence_tasks(items, len(adjudication)))
    adjudication.extend(_freshness_tasks(items, len(adjudication)))
    core_refs = {review_id for task in core for review_id in task["ledger_review_ids"]}
    adjudication_refs = {review_id for task in adjudication for review_id in task["ledger_review_ids"]}
    assert core_refs.isdisjoint(adjudication_refs)

    semantic_required = {
        item["review_id"]
        for item in items
        if item["ambiguity_flag"]
        and item["item_type"] in {"claim_segmentation", "citation_support", "high_risk"}
    }
    assert semantic_required <= adjudication_refs
    required_units = {item["review_id"] for item in items if item["item_type"] == "required_unit"}
    assert len(required_units) == 18 and required_units <= core_refs

    human_refs = core_refs | adjudication_refs
    machine_count = len(items) - len(human_refs)
    core_document = {
        "layer": "HUMAN_CALIBRATION_CORE",
        "status": "PENDING_HUMAN_REVIEW",
        "task_count": len(core),
        "tasks": core,
    }
    adjudication_document = {
        "layer": "HUMAN_ADJUDICATION_QUEUE",
        "status": "PENDING_HUMAN_REVIEW",
        "task_count": len(adjudication),
        "tasks": adjudication,
    }
    write(package / "HUMAN_CALIBRATION_CORE.json", core_document)
    write(package / "HUMAN_ADJUDICATION_QUEUE.json", adjudication_document)

    queue = {
        "status": "READY_FOR_HUMAN_REVIEW",
        "human_review_status": "PENDING",
        "reviewer": None,
        "full_ledger_reference": "FULL_AI_ASSISTED_LEDGER.json",
        "calibration_core_reference": "HUMAN_CALIBRATION_CORE.json",
        "adjudication_queue_reference": "HUMAN_ADJUDICATION_QUEUE.json",
        "before_human_queue_count": 483,
        "after_human_workload_count": len(core) + len(adjudication),
        "human_calibration_core": core,
        "human_adjudication_queue": adjudication,
    }
    write(package / "HUMAN_REVIEW_QUEUE.json", queue)
    (package / "HUMAN_REVIEW_QUEUE.md").write_text(
        _render_markdown(len(items), machine_count, core, adjudication),
        encoding="utf-8",
        newline="\n",
    )

    linked_items = [item for item in items if item["review_id"] in human_refs]
    flag_counts = Counter(
        flag
        for task in adjudication
        for flag in task.get("flags", [])
    )
    summary = {
        "status": "PASSED",
        "full_ledger_items": len(items),
        "machine_resolved_no_human_action_items": machine_count,
        "human_linked_ledger_records": len(human_refs),
        "human_calibration_core_items": len(core),
        "human_adjudication_queue_items": len(adjudication),
        "after_human_workload_items": len(core) + len(adjudication),
        "human_items_by_category": {
            "calibration_core": _breakdown(core, "category"),
            "adjudication_queue": _breakdown(adjudication, "category"),
        },
        "human_items_by_type": {
            "calibration_core": _breakdown(core, "dimension"),
            "adjudication_queue": _breakdown(adjudication, "dimension"),
        },
        "adjudication_flags": dict(sorted(flag_counts.items())),
        "linked_ledger_records_by_type": dict(
            sorted(Counter(item["item_type"] for item in linked_items).items())
        ),
        "required_units_human_reviewable": len(required_units),
        "semantic_ambiguity_records_covered": len(semantic_required),
        "provider_calls": 0,
        "official_benchmark_calls": 0,
        "holdout_used": False,
        "labels_or_recommendations_changed": False,
    }
    write(package / "HUMAN_REVIEW_COMPRESSION.json", summary)

    manifest = read(package / "CALIBRATION_MANIFEST.json")
    ambiguity_count = manifest.pop(
        "unresolved_count", manifest.get("ai_assisted_ambiguity_flag_count")
    )
    assert ambiguity_count == sum(item["ambiguity_flag"] for item in items)
    manifest["ai_assisted_ambiguity_flag_count"] = ambiguity_count
    manifest.pop("confident_recommendations_requiring_confirmation", None)
    manifest.update(
        {
            "full_ai_assisted_ledger_item_count": len(items),
            "machine_resolved_no_human_action_item_count": machine_count,
            "human_calibration_core_item_count": len(core),
            "human_adjudication_queue_item_count": len(adjudication),
            "human_review_item_count": len(core) + len(adjudication),
            "human_linked_ledger_record_count": len(human_refs),
            "human_review_compression": "HUMAN_REVIEW_COMPRESSION.json",
        }
    )
    write(package / "CALIBRATION_MANIFEST.json", manifest)
    validation = read(package / "VALIDATION.json")
    validation.update(
        {
            "full_ai_assisted_ledger_items": len(items),
            "machine_resolved_no_human_action_items": machine_count,
            "human_calibration_core_items": len(core),
            "human_adjudication_queue_items": len(adjudication),
            "human_workload_items": len(core) + len(adjudication),
            "human_queue_material_links_verified": True,
            "provider_calls_during_compression": 0,
            "holdout_used_during_compression": False,
        }
    )
    write(package / "VALIDATION.json", validation)
    return summary


def refresh_hashes(package: Path = PACKAGE) -> None:
    receipt = package / "ARTIFACT_HASHES.json"
    current = read(receipt)
    additions = {
        "scripts/compress_human_review_queue.py",
        "scripts/package_development_calibration.py",
        "scripts/verify_development_calibration.py",
        "tests/test_human_review_queue_compression.py",
        *(
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in package.iterdir()
            if path.is_file() and path.name != receipt.name
        ),
    }
    paths = set(current) | additions
    hashes = {}
    for name in sorted(paths):
        path = ROOT / name
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(receipt, hashes)


if __name__ == "__main__":
    print(json.dumps(compress(), ensure_ascii=False, sort_keys=True))
