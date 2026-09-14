"""Freeze the human-reviewed development calibration package offline.

This is a bounded artifact finalizer. It does not execute the agent, read the
holdout split, call a provider, or modify the full AI-assisted ledger.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PACKAGE = ROOT / "docs/v2/calibration/v2.2.0"
DATASET = ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json"
RUBRIC = ROOT / "docs/v2/V2_BENCHMARK_SPEC.md"
DATASET_SHA256 = "95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa"
RUBRIC_VERSION = "enterprise-insight-bench-v2/2.2.0"
REVIEWER = "human-reviewer-calibration-001"
CASE_IDS = [
    "EIV2_FV_001",
    "EIV2_TC_001",
    "EIV2_CC_001",
    "EIV2_TM_003",
    "EIV2_CR_003",
    "EIV2_ED_002",
]
HUMAN_FIELDS = (
    "human_review_status",
    "reviewer_identity",
    "human_decision",
    "review_timestamp",
    "adjudication_note",
)
HUMAN_VALUE_FIELDS = (
    "reviewer_identity",
    "human_decision",
    "review_timestamp",
    "adjudication_note",
)
FAILURE_TYPES = {
    "TASK_COVERAGE_FAILURE",
    "EVIDENCE_STRENGTH_FAILURE",
    "PRIMARY_SOURCE_GAP",
    "INDEPENDENCE_GAP",
    "FRESHNESS_GAP",
    "QUALIFICATION_METADATA_GAP",
    "SAFE_ABSTENTION",
    "GENERATION_ALIGNMENT_FAILURE",
    "EVIDENCE_SCOPE_MISMATCH",
}


def read(path: Path) -> Any:
    def reject(value: str) -> None:
        raise ValueError(f"Non-finite JSON value: {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def source_count(item: dict[str, Any]) -> int:
    """Count deduplicated saved source references, not chunks or URL variants.

    This is intentionally a conservative source-group diagnostic. It is not a
    claim that distinct URLs prove independent publisher organizations.
    """
    urls = {saved["source_reference"] for saved in item.get("saved_evidence", [])}
    normalized = {url.split("?", 1)[0].rstrip("/") for url in urls}
    return len(normalized)


def accepted_note() -> str:
    return "accepted AI recommendation"


def human_decision_for_item(item: dict[str, Any]) -> tuple[str, str]:
    overrides = {
        "EIV2_FV_001-required_unit-001": (
            "SATISFIED",
            "human override + reason: saved official policy evidence supports the default no-training rule.",
        ),
        "EIV2_TC_001-required_unit-003": (
            "NOT_SATISFIED",
            "human override + reason: the report contains workload limitations, but the frozen two-independent strength obligation is not met.",
        ),
    }
    if item["review_id"] in overrides:
        return overrides[item["review_id"]]
    return item["ai_recommendation"], accepted_note()


def task_decision(task: dict[str, Any], ledger_by_id: dict[str, dict[str, Any]]) -> tuple[Any, str]:
    records = [ledger_by_id[review_id] for review_id in task["ledger_review_ids"]]
    decisions = [human_decision_for_item(item) for item in records]
    if task["dimension"] == "required_unit":
        assert len(records) == 1
        return decisions[0]
    assert all(note == accepted_note() for _, note in decisions)
    return "ACCEPTED_AI_RECOMMENDATIONS", accepted_note()


def finalize_task(task: dict[str, Any], ledger_by_id: dict[str, dict[str, Any]], timestamp: str) -> None:
    decision, note = task_decision(task, ledger_by_id)
    if task.get("human_review_status") == "COMPLETED":
        assert task.get("human_decision") == decision
        assert task.get("reviewer_identity") == REVIEWER
        assert task.get("review_timestamp") == timestamp
        assert task.get("adjudication_note") == note
        return
    assert task.get("human_review_status") == "PENDING"
    assert all(task.get(field) is None for field in HUMAN_VALUE_FIELDS)
    task["human_decision"] = decision
    task["human_review_status"] = "COMPLETED"
    task["reviewer_identity"] = REVIEWER
    task["review_timestamp"] = timestamp
    task["adjudication_note"] = note


def update_record(record: dict[str, Any], timestamp: str) -> None:
    decision, note = human_decision_for_item(record)
    record["human_decision"] = decision
    record["human_review_status"] = "COMPLETED"
    record["reviewer_identity"] = REVIEWER
    record["review_timestamp"] = timestamp
    record["review_date"] = timestamp[:10]
    record["adjudication_note"] = note


def failure_record(
    case_id: str,
    category: str,
    required_unit_id: str,
    required_unit: str,
    final_human_decision: str,
    final_report_coverage: str,
    evidence_available: bool,
    primary_source_available: bool,
    independent_source_count: int,
    freshness_status: str,
    gate_effect: str,
    dominant_failure_type: str | None,
    secondary_failure_types: list[str],
    reason: str,
) -> dict[str, Any]:
    if dominant_failure_type is not None:
        assert dominant_failure_type in FAILURE_TYPES
    assert all(value in FAILURE_TYPES for value in secondary_failure_types)
    return {
        "case_id": case_id,
        "category": category,
        "required_unit": required_unit,
        "required_unit_id": required_unit_id,
        "final_human_decision": final_human_decision,
        "final_report_coverage": final_report_coverage,
        "evidence_available": evidence_available,
        "primary_source_available": primary_source_available,
        "independent_source_count": independent_source_count,
        "freshness_status": freshness_status,
        "gate_effect": gate_effect,
        "dominant_failure_type": dominant_failure_type,
        "secondary_failure_types": secondary_failure_types,
        "concise_evidence_based_reason": reason,
    }


def build_failure_map(
    required_items: list[dict[str, Any]],
    source_commit_value: str,
) -> dict[str, Any]:
    categories = {item["case_id"]: item["category"] for item in required_items}
    by_id = {item["review_id"]: item for item in required_items}

    curated: dict[str, dict[str, Any]] = {
        "EIV2_FV_001-required_unit-001": failure_record(
            "EIV2_FV_001", categories["EIV2_FV_001"], "training_default", "默认训练用途政策",
            "SATISFIED", "full", True, True, 3, "not_required", "hedge", None, [],
            "人审接受该条报告中的限定性边界表述；保存的官方政策片段支持默认不训练规则，因此 UNCERTAIN 被覆盖为 SATISFIED。",
        ),
        "EIV2_FV_001-required_unit-002": failure_record(
            "EIV2_FV_001", categories["EIV2_FV_001"], "exceptions", "明确适用例外",
            "NOT_SATISFIED", "partial", True, False, 3, "not_required", "hedge",
            "EVIDENCE_STRENGTH_FAILURE",
            ["PRIMARY_SOURCE_GAP", "INDEPENDENCE_GAP", "QUALIFICATION_METADATA_GAP"],
            "报告只保留社区帖子提出的去标识化/匿名化例外争议，并明确标为未确认；保存材料未形成该例外的合格一手或足够独立支持。",
        ),
        "EIV2_FV_001-required_unit-003": failure_record(
            "EIV2_FV_001", categories["EIV2_FV_001"], "retention", "数据保留或控制边界",
            "NOT_SATISFIED", "partial", True, True, 1, "unverified", "emit",
            "TASK_COVERAGE_FAILURE",
            ["EVIDENCE_SCOPE_MISMATCH", "EVIDENCE_STRENGTH_FAILURE", "FRESHNESS_GAP"],
            "最终报告只说明滥用监控日志和应用状态等存储类型，没有覆盖保留期限、删除或控制边界；唯一关联证据的 publication_date 仍为空。",
        ),
        "EIV2_TC_001-required_unit-001": failure_record(
            "EIV2_TC_001", categories["EIV2_TC_001"], "hybrid", "混合检索机制",
            "NOT_SATISFIED", "full", True, False, 2, "not_required", "emit",
            "PRIMARY_SOURCE_GAP",
            ["INDEPENDENCE_GAP", "EVIDENCE_STRENGTH_FAILURE", "QUALIFICATION_METADATA_GAP"],
            "报告清楚描述向量相似度与关键词/元数据过滤的混合机制，但保存引用是教程/文章组合，未建立 pgvector 一手材料加独立佐证。",
        ),
        "EIV2_TC_001-required_unit-002": failure_record(
            "EIV2_TC_001", categories["EIV2_TC_001"], "indexes", "索引选择与权衡",
            "NOT_SATISFIED", "partial", True, False, 2, "not_required", "emit",
            "TASK_COVERAGE_FAILURE",
            ["PRIMARY_SOURCE_GAP", "EVIDENCE_STRENGTH_FAILURE", "QUALIFICATION_METADATA_GAP"],
            "报告相关段落只说明查询规划器可以使用索引和 SQL 组合，没有组织 HNSW/IVFFlat 的选择与权衡；相关证据也不是目标产品的一手文档。",
        ),
        "EIV2_TC_001-required_unit-003": failure_record(
            "EIV2_TC_001", categories["EIV2_TC_001"], "limits", "企业工作负载限制",
            "NOT_SATISFIED", "full", True, False, 2, "not_required", "emit",
            "INDEPENDENCE_GAP",
            ["EVIDENCE_STRENGTH_FAILURE", "QUALIFICATION_METADATA_GAP"],
            "报告给出多项生产限制，但两条 VeloDB 证据属于同一页面，另一条 ParadeDB 文章未提供足以完成冻结 two_independent obligation 的资格化元数据。",
        ),
        "EIV2_CC_001-required_unit-001": failure_record(
            "EIV2_CC_001", categories["EIV2_CC_001"], "model_choice", "模型选择对比",
            "NOT_SATISFIED", "none", True, False, 1, "unverified", "omit/no_claims_emitted",
            "SAFE_ABSTENTION",
            ["EVIDENCE_STRENGTH_FAILURE", "PRIMARY_SOURCE_GAP", "INDEPENDENCE_GAP", "QUALIFICATION_METADATA_GAP"],
            "最终报告只有固定的无断言说明；Gate 因比较所需 two_independent 与每个实体的 comparable primary 未满足而 omit，selected evidence 仅用于解释省略原因。",
        ),
        "EIV2_CC_001-required_unit-002": failure_record(
            "EIV2_CC_001", categories["EIV2_CC_001"], "governance_network", "治理与网络隔离对比",
            "NOT_SATISFIED", "none", True, False, 1, "unverified", "omit/no_claims_emitted",
            "SAFE_ABSTENTION",
            ["EVIDENCE_STRENGTH_FAILURE", "PRIMARY_SOURCE_GAP", "INDEPENDENCE_GAP", "QUALIFICATION_METADATA_GAP"],
            "最终报告没有治理或网络隔离比较内容；Gate/grounding artifacts 显示没有可发出的 claims，保存的第三方材料未满足比较来源义务。",
        ),
        "EIV2_CC_001-required_unit-003": failure_record(
            "EIV2_CC_001", categories["EIV2_CC_001"], "pricing", "定价透明度对比",
            "NOT_SATISFIED", "none", True, False, 1, "unverified", "omit/no_claims_emitted",
            "SAFE_ABSTENTION",
            ["EVIDENCE_STRENGTH_FAILURE", "PRIMARY_SOURCE_GAP", "INDEPENDENCE_GAP", "QUALIFICATION_METADATA_GAP"],
            "最终报告没有定价透明度比较内容；Gate 对比较实体的一手来源与独立支持要求均未满足，因此没有 emitted claim 可覆盖该 Required Unit。",
        ),
        "EIV2_TM_003-required_unit-001": failure_record(
            "EIV2_TM_003", categories["EIV2_TM_003"], "regions", "区域扩张趋势",
            "NOT_SATISFIED", "partial", True, False, 1, "unverified", "emit",
            "INDEPENDENCE_GAP",
            ["EVIDENCE_STRENGTH_FAILURE", "TASK_COVERAGE_FAILURE", "FRESHNESS_GAP", "QUALIFICATION_METADATA_GAP"],
            "报告写到主权云与区域基础设施趋势，但两个关联片段是同一 InfotechLead/ABI Research 报道的 URL 变体，且未完整比较主要云厂商服务的区域扩张；strict freshness 也未资格化。",
        ),
        "EIV2_TM_003-required_unit-002": failure_record(
            "EIV2_TM_003", categories["EIV2_TM_003"], "models", "模型多样化趋势",
            "NOT_SATISFIED", "partial", True, False, 1, "unverified", "emit",
            "INDEPENDENCE_GAP",
            ["FRESHNESS_GAP", "EVIDENCE_STRENGTH_FAILURE", "TASK_COVERAGE_FAILURE", "QUALIFICATION_METADATA_GAP"],
            "报告提供模型接入清单，但两个引用来自同一 Bits Lovers 页面，publication_date 未验证，未形成 two_independent 的时效趋势证据。",
        ),
        "EIV2_TM_003-required_unit-003": failure_record(
            "EIV2_TM_003", categories["EIV2_TM_003"], "controls", "企业控制趋势",
            "NOT_SATISFIED", "partial", True, True, 2, "unverified", "emit",
            "FRESHNESS_GAP",
            ["TASK_COVERAGE_FAILURE", "EVIDENCE_STRENGTH_FAILURE", "QUALIFICATION_METADATA_GAP"],
            "报告同时引用 AWS 治理建议与 Clarip 产品描述，但没有完整建立主要云厂商控制能力的发展趋势，且 strict freshness 证据未确认。",
        ),
        "EIV2_CR_003-required_unit-001": failure_record(
            "EIV2_CR_003", categories["EIV2_CR_003"], "vendor_score", "厂商报告分数",
            "NOT_SATISFIED", "none", True, True, 1, "not_required", "omit/no_claims_emitted",
            "SAFE_ABSTENTION",
            ["EVIDENCE_STRENGTH_FAILURE", "EVIDENCE_SCOPE_MISMATCH", "QUALIFICATION_METADATA_GAP"],
            "最终报告没有 emitted claim；保存材料中虽有 DeepSeek 官方项目来源，但分数需要更完整的厂商结果与冻结强度规则，Gate 因义务未满足而 omit。",
        ),
        "EIV2_CR_003-required_unit-002": failure_record(
            "EIV2_CR_003", categories["EIV2_CR_003"], "replication", "第三方复现结果",
            "NOT_SATISFIED", "none", True, False, 1, "not_required", "omit/no_claims_emitted",
            "SAFE_ABSTENTION",
            ["EVIDENCE_SCOPE_MISMATCH", "EVIDENCE_STRENGTH_FAILURE", "INDEPENDENCE_GAP", "QUALIFICATION_METADATA_GAP"],
            "最终报告没有 emitted claim；HF discussion 讨论的是 DeepScaleR-1.5B-Preview，不能直接替代目标完整 DeepSeek-R1 的第三方复现结果。",
        ),
        "EIV2_CR_003-required_unit-003": failure_record(
            "EIV2_CR_003", categories["EIV2_CR_003"], "explanation", "差异解释与可信判断",
            "NOT_SATISFIED", "none", True, True, 2, "not_required", "omit/no_claims_emitted",
            "SAFE_ABSTENTION",
            ["EVIDENCE_SCOPE_MISMATCH", "EVIDENCE_STRENGTH_FAILURE", "INDEPENDENCE_GAP", "QUALIFICATION_METADATA_GAP"],
            "最终报告没有 emitted claim；保存材料包含官方 R1 项目与 DeepScaleR 讨论，但对象/版本范围不一致，不能直接形成差异解释与可信判断。",
        ),
        "EIV2_ED_002-required_unit-001": failure_record(
            "EIV2_ED_002", categories["EIV2_ED_002"], "capabilities", "候选技术能力",
            "NOT_SATISFIED", "partial", True, True, 2, "not_required", "emit",
            "TASK_COVERAGE_FAILURE",
            ["GENERATION_ALIGNMENT_FAILURE", "EVIDENCE_SCOPE_MISMATCH", "INDEPENDENCE_GAP", "QUALIFICATION_METADATA_GAP"],
            "最终报告主要解释 pgvector 的定义与能力，没有围绕托管向量库和搜索引擎候选集合完成对比；已有材料不足以补齐未生成的候选侧内容。",
        ),
        "EIV2_ED_002-required_unit-002": failure_record(
            "EIV2_ED_002", categories["EIV2_ED_002"], "operations", "规模与运维条件",
            "NOT_SATISFIED", "partial", True, False, 1, "not_required", "emit",
            "EVIDENCE_STRENGTH_FAILURE",
            ["INDEPENDENCE_GAP", "TASK_COVERAGE_FAILURE", "QUALIFICATION_METADATA_GAP"],
            "报告发出 Milvus 部署和 pgvector 运维相关内容，但主要运维比较来自同一社区文章，未建立 two_independent，规模与版本边界也不完整。",
        ),
        "EIV2_ED_002-required_unit-003": failure_record(
            "EIV2_ED_002", categories["EIV2_ED_002"], "migration", "条件化迁移建议",
            "NOT_SATISFIED", "partial", True, False, 1, "unverified", "emit",
            "TASK_COVERAGE_FAILURE",
            ["GENERATION_ALIGNMENT_FAILURE", "EVIDENCE_SCOPE_MISMATCH", "FRESHNESS_GAP", "QUALIFICATION_METADATA_GAP"],
            "最终报告只给出按向量规模、查询模式和架构偏好的选型原则，没有给中型制造企业的条件化迁移步骤或边界；关联 CSDN 材料的日期归属仍有疑点。",
        ),
    }
    assert set(curated) == set(by_id)

    records = []
    for review_id in sorted(curated):
        item = deepcopy(curated[review_id])
        item["source_commit"] = source_commit_value
        records.append(item)

    dominant = Counter(
        record["dominant_failure_type"]
        for record in records
        if record["dominant_failure_type"] is not None
    )
    category_summary: dict[str, dict[str, int]] = {}
    for record in records:
        category = record["category"]
        category_summary.setdefault(category, Counter())
        key = record["dominant_failure_type"] or "NO_FAILURE"
        category_summary[category][key] += 1

    work_packages = [
        {
            "name": "requirement-driven research/generation",
            "addresses_failure_types": [
                "TASK_COVERAGE_FAILURE",
                "GENERATION_ALIGNMENT_FAILURE",
            ],
            "mapped_required_units": [
                "EIV2_FV_001/retention",
                "EIV2_TC_001/indexes",
                "EIV2_TM_003/regions",
                "EIV2_TM_003/controls",
                "EIV2_ED_002/capabilities",
                "EIV2_ED_002/migration",
            ],
            "scope": "mapping only; feature not implemented in Batch 0",
        },
        {
            "name": "source/date metadata enrichment",
            "addresses_failure_types": [
                "PRIMARY_SOURCE_GAP",
                "QUALIFICATION_METADATA_GAP",
                "FRESHNESS_GAP",
            ],
            "mapped_required_units": [
                "EIV2_FV_001/exceptions",
                "EIV2_FV_001/retention",
                "EIV2_TC_001/hybrid",
                "EIV2_TC_001/indexes",
                "EIV2_TC_001/limits",
                "EIV2_CC_001/model_choice",
                "EIV2_CC_001/governance_network",
                "EIV2_CC_001/pricing",
                "EIV2_TM_003/regions",
                "EIV2_TM_003/models",
                "EIV2_TM_003/controls",
                "EIV2_ED_002/migration",
            ],
            "scope": "mapping only; feature not implemented in Batch 0",
        },
        {
            "name": "one bounded evidence-gap retrieval",
            "addresses_failure_types": [
                "EVIDENCE_STRENGTH_FAILURE",
                "PRIMARY_SOURCE_GAP",
                "INDEPENDENCE_GAP",
                "FRESHNESS_GAP",
                "EVIDENCE_SCOPE_MISMATCH",
            ],
            "mapped_required_units": [
                "EIV2_FV_001/exceptions",
                "EIV2_FV_001/retention",
                "EIV2_TC_001/hybrid",
                "EIV2_TC_001/indexes",
                "EIV2_TC_001/limits",
                "EIV2_CC_001/model_choice",
                "EIV2_CC_001/governance_network",
                "EIV2_CC_001/pricing",
                "EIV2_TM_003/regions",
                "EIV2_TM_003/models",
                "EIV2_TM_003/controls",
                "EIV2_CR_003/vendor_score",
                "EIV2_CR_003/replication",
                "EIV2_CR_003/explanation",
                "EIV2_ED_002/operations",
            ],
            "scope": "mapping only; feature not implemented in Batch 0",
        },
        {
            "name": "layered evidence disclosure + evidence-grounded AI inference",
            "addresses_failure_types": [
                "SAFE_ABSTENTION",
                "GENERATION_ALIGNMENT_FAILURE",
                "EVIDENCE_SCOPE_MISMATCH",
            ],
            "mapped_required_units": [
                "EIV2_CC_001/model_choice",
                "EIV2_CC_001/governance_network",
                "EIV2_CC_001/pricing",
                "EIV2_CR_003/vendor_score",
                "EIV2_CR_003/replication",
                "EIV2_CR_003/explanation",
                "EIV2_ED_002/capabilities",
                "EIV2_ED_002/migration",
            ],
            "scope": "mapping only; feature not implemented in Batch 0",
        },
    ]
    return {
        "schema_version": "enterprise-insight-v2-development-failure-map/1.0.0",
        "benchmark_schema": RUBRIC_VERSION,
        "dataset_sha256": DATASET_SHA256,
        "cutoff": "2026-09-05",
        "source_commit": source_commit_value,
        "record_count": len(records),
        "field_semantics": {
            "final_report_coverage": "full means the report substantively addresses the unit; partial means related content omits an obligation; none means no emitted report claim.",
            "independent_source_count": "deduplicated saved source references; repeated chunks and URL variants are collapsed, and this count does not by itself prove independent publisher organizations.",
            "freshness_status": "verified means a publication date was verified; it does not imply the age window is satisfied. not_required means the RU has no frozen freshness obligation; unverified means the saved record did not qualify a usable date.",
            "gate_effect": "observed final report/gate outcome for the material linked to the Required Unit; it is not itself a human Required Unit decision.",
        },
        "closed_failure_taxonomy": sorted(FAILURE_TYPES),
        "records": records,
        "summary": {
            "required_unit_count": len(records),
            "final_human_decision_counts": dict(sorted(Counter(record["final_human_decision"] for record in records).items())),
            "dominant_failure_type_counts": dict(sorted(dominant.items())),
            "category_distribution": {
                category: dict(sorted(counts.items()))
                for category, counts in sorted(category_summary.items())
            },
            "planned_utility_correction_work_packages": work_packages,
        },
    }


def render_failure_map_markdown(failure_map: dict[str, Any]) -> str:
    summary = failure_map["summary"]
    lines = [
        "# V2.2.0 Development Failure Map",
        "",
        "This map freezes the human-reviewed development baseline before any bounded utility correction. It is an evidence-based mapping artifact, not a feature implementation or a claim that the system failed on holdout.",
        "",
        "## Scope and semantics",
        "",
        f"- Benchmark schema: `{failure_map['benchmark_schema']}`",
        f"- Dataset SHA-256: `{failure_map['dataset_sha256']}`",
        f"- Information cutoff: `{failure_map['cutoff']}`",
        f"- Source commit before freeze: `{failure_map['source_commit']}`",
        f"- Required Units: {failure_map['record_count']}; final human result: 1 SATISFIED / 17 NOT_SATISFIED",
        "- `final_report_coverage`: `full` means substantive report coverage, `partial` means related content misses an obligation, and `none` means no emitted report claim.",
        "- `independent_source_count` is a deduplicated saved-source diagnostic. Repeated chunks and URL variants are collapsed; distinct URLs do not automatically prove independent publisher organizations.",
        "- `verified` in freshness metadata means the publication date itself was verified. It does not automatically mean the frozen age window was satisfied.",
        "",
        "## Required Unit records",
        "",
        "| Case | Category | Required Unit | Human | Report coverage | Evidence | Primary | Independent source count | Freshness | Gate effect | Dominant failure |",
        "|---|---|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for record in failure_map["records"]:
        lines.append(
            "| {case_id} | {category} | {required_unit} | {final_human_decision} | {final_report_coverage} | {evidence_available} | {primary_source_available} | {independent_source_count} | {freshness_status} | {gate_effect} | {dominant_failure_type} |".format(
                **{**record, "dominant_failure_type": record["dominant_failure_type"] or "NO_FAILURE"}
            )
        )
    lines.extend(["", "### Evidence-based rationale", ""])
    for record in failure_map["records"]:
        lines.extend(
            [
                f"#### {record['case_id']} / {record['required_unit_id']} — {record['required_unit']}",
                "",
                f"- Dominant: `{record['dominant_failure_type'] or 'NO_FAILURE'}`",
                f"- Secondary: {', '.join(f'`{value}`' for value in record['secondary_failure_types']) or 'none'}",
                f"- Reason: {record['concise_evidence_based_reason']}",
                "",
            ]
        )
    lines.extend(["## Summary", "", "### Dominant failure distribution", ""])
    for name, count in summary["dominant_failure_type_counts"].items():
        lines.append(f"- `{name}`: {count}")
    lines.extend(["- `NO_FAILURE` (the one human-satisfied RU): 1", "", "### Category distribution", ""])
    for category, counts in summary["category_distribution"].items():
        details = ", ".join(f"`{name}`={count}" for name, count in counts.items())
        lines.append(f"- `{category}`: {details}")
    lines.extend(["", "### Planned utility-correction mapping", ""])
    for package in summary["planned_utility_correction_work_packages"]:
        lines.extend(
            [
                f"#### {package['name']}",
                "",
                f"- Failure types: {', '.join(f'`{value}`' for value in package['addresses_failure_types'])}",
                f"- Required Units: {', '.join(f'`{value}`' for value in package['mapped_required_units'])}",
                f"- Scope: {package['scope']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Integrity boundary",
            "",
            "This artifact uses only saved development reports, selected evidence, execution Gate/Grounding artifacts, and the frozen calibration records. It does not inspect or execute holdout cases, call providers, change the rubric, or implement any of the four work packages.",
            "",
        ]
    )
    return "\n".join(lines)


def finalize(timestamp: str) -> dict[str, Any]:
    source_commit_value = source_commit()
    assert digest(DATASET) == DATASET_SHA256
    manifest_before = read(PACKAGE / "CALIBRATION_MANIFEST.json")
    assert manifest_before["benchmark_schema"] == RUBRIC_VERSION
    assert manifest_before["dataset_sha256"] == DATASET_SHA256
    assert manifest_before["official_holdout_executions"] == 0
    assert digest(RUBRIC) == read(PACKAGE / "FROZEN_RULE_REFERENCES.json")["protocol_sha256"]
    before = {
        "full_ledger": digest(PACKAGE / "FULL_AI_ASSISTED_LEDGER.json"),
        "dataset": digest(DATASET),
        "rubric": digest(RUBRIC),
        "v2_runtime_files": {
            str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
            for path in sorted((ROOT / "gpt_researcher").rglob("*.py"))
        },
    }
    full_ledger = read(PACKAGE / "FULL_AI_ASSISTED_LEDGER.json")
    assert full_ledger["status"] == "AI_ASSISTED" and full_ledger["final_gold"] is False
    ledger_by_id = {item["review_id"]: item for item in full_ledger["items"]}
    assert len(ledger_by_id) == 483

    core_doc = read(PACKAGE / "HUMAN_CALIBRATION_CORE.json")
    adj_doc = read(PACKAGE / "HUMAN_ADJUDICATION_QUEUE.json")
    core = core_doc["tasks"]
    adjudication = adj_doc["tasks"]
    tasks = core + adjudication
    assert len(tasks) == 87
    assert {task["case_id"] for task in tasks} <= set(CASE_IDS)
    assert all(review_id in ledger_by_id for task in tasks for review_id in task["ledger_review_ids"])
    for task in tasks:
        finalize_task(task, ledger_by_id, timestamp)

    for filename, document in (
        ("HUMAN_CALIBRATION_CORE.json", core_doc),
        ("HUMAN_ADJUDICATION_QUEUE.json", adj_doc),
    ):
        document["status"] = "HUMAN_REVIEW_COMPLETED"
        document["reviewer"] = REVIEWER
        document["review_timestamp"] = timestamp
        write(PACKAGE / filename, document)

    linked_ids = {review_id for task in tasks for review_id in task["ledger_review_ids"]}
    assert len(linked_ids) == 256
    for case_id in CASE_IDS:
        category = next(case["category"] for case in manifest_before["cases"] if case["case_id"] == case_id)
        sheet_path = PACKAGE / category / case_id / "review_sheet.json"
        sheet = read(sheet_path)
        assert sheet["case_id"] == case_id
        selected_ids = {
            review_id
            for task in tasks
            if task["case_id"] == case_id
            for review_id in task["ledger_review_ids"]
        }
        for section in ("claim_segmentation", "citation_support", "required_unit", "evidence_strength", "independence", "freshness", "high_risk"):
            for record in sheet.get(section + "_review", []):
                if record["review_id"] in selected_ids:
                    update_record(record, timestamp)
                    assert record["ai_recommendation"] == ledger_by_id[record["review_id"]]["ai_recommendation"]
        sheet["status"] = "HUMAN_REVIEW_COMPLETED"
        sheet["human_review_status"] = "COMPLETED"
        sheet["reviewer"] = REVIEWER
        sheet["review_timestamp"] = timestamp
        write(sheet_path, sheet)
        case_hashes_path = sheet_path.parent / "hashes.json"
        case_hashes = read(case_hashes_path)
        for name in list(case_hashes):
            target = Path(name)
            if not target.is_absolute():
                target = ROOT / target
            if target.is_file():
                case_hashes[name] = digest(target)
        write(case_hashes_path, case_hashes)

    queue = read(PACKAGE / "HUMAN_REVIEW_QUEUE.json")
    queue["status"] = "HUMAN_REVIEW_COMPLETED"
    queue["human_review_status"] = "COMPLETED"
    queue["reviewer"] = REVIEWER
    queue["review_timestamp"] = timestamp
    queue["human_calibration_core"] = core
    queue["human_adjudication_queue"] = adjudication
    write(PACKAGE / "HUMAN_REVIEW_QUEUE.json", queue)

    from scripts.compress_human_review_queue import _render_markdown

    markdown = _render_markdown(483, 227, core, adjudication)
    markdown = markdown.replace("Status: **READY_FOR_HUMAN_REVIEW**. All recommendations remain AI-assisted; all human fields remain unset.",
                                f"Status: **HUMAN_REVIEW_COMPLETED**. Reviewer: `{REVIEWER}`. Review timestamp: `{timestamp}`.")
    for task in [*core, *adjudication]:
        marker = "Human decision: PENDING"
        assert marker in markdown
        markdown = markdown.replace(marker, f"Human decision: {task['human_decision']}", 1)
    markdown += "\nHuman decisions are finalized in the JSON layers and case review sheets. The full AI-assisted ledger remains unchanged.\n"
    (PACKAGE / "HUMAN_REVIEW_QUEUE.md").write_text(markdown, encoding="utf-8", newline="\n")

    required_items = [item for item in full_ledger["items"] if item["item_type"] == "required_unit"]
    failure_map = build_failure_map(required_items, source_commit_value)
    write(PACKAGE / "DEVELOPMENT_FAILURE_MAP.json", failure_map)
    (PACKAGE / "DEVELOPMENT_FAILURE_MAP.md").write_text(
        render_failure_map_markdown(failure_map), encoding="utf-8", newline="\n"
    )

    map_hashes = {
        "DEVELOPMENT_FAILURE_MAP.json": digest(PACKAGE / "DEVELOPMENT_FAILURE_MAP.json"),
        "DEVELOPMENT_FAILURE_MAP.md": digest(PACKAGE / "DEVELOPMENT_FAILURE_MAP.md"),
    }
    calibration_files = [
        "HUMAN_CALIBRATION_CORE.json",
        "HUMAN_ADJUDICATION_QUEUE.json",
        "HUMAN_REVIEW_QUEUE.json",
        "HUMAN_REVIEW_QUEUE.md",
        "HUMAN_REVIEW_COMPRESSION.json",
        "CALIBRATION_MANIFEST.json",
        "VALIDATION.json",
        "DEVELOPMENT_FAILURE_MAP.json",
        "DEVELOPMENT_FAILURE_MAP.md",
        "DEVELOPMENT_CALIBRATION_FREEZE.json",
    ]
    manifest = deepcopy(manifest_before)
    manifest.update(
        {
            "package_status": "HUMAN_CALIBRATION_COMPLETED",
            "human_review_status": "COMPLETED",
            "reviewer": REVIEWER,
            "review_timestamp": timestamp,
            "human_review_completion": {
                "status": "COMPLETED",
                "task_count": 87,
                "finalized_count": 87,
                "reviewer": REVIEWER,
                "review_timestamp": timestamp,
            },
            "required_unit_baseline": {
                "satisfied": 1,
                "not_satisfied": 17,
                "total": 18,
                "completion": "1/18",
            },
            "development_failure_map": map_hashes,
            "development_calibration_freeze": "DEVELOPMENT_CALIBRATION_FREEZE.json",
            "provider_calls": 0,
            "official_holdout_executions": 0,
            "calibration_artifact_files": calibration_files,
        }
    )
    for case in manifest["cases"]:
        case["human_review_status"] = "COMPLETED"
        case["reviewer"] = REVIEWER
        case["review_timestamp"] = timestamp
    write(PACKAGE / "CALIBRATION_MANIFEST.json", manifest)

    compression = read(PACKAGE / "HUMAN_REVIEW_COMPRESSION.json")
    compression.update(
        {
            "human_review_status": "COMPLETED",
            "reviewer": REVIEWER,
            "review_timestamp": timestamp,
            "finalized_human_review_items": 87,
            "required_unit_result": "1/18",
            "development_failure_map": map_hashes,
        }
    )
    write(PACKAGE / "HUMAN_REVIEW_COMPRESSION.json", compression)

    validation = read(PACKAGE / "VALIDATION.json")
    validation.update(
        {
            "status": "PASSED",
            "human_fields_unset": False,
            "human_review_status": "COMPLETED",
            "human_review_tasks_finalized": 87,
            "required_unit_result": "1/18",
            "full_ai_assisted_ledger_preserved": True,
            "dataset_sha256_verified": DATASET_SHA256,
            "benchmark_rubric_unchanged": True,
            "agent_runtime_unchanged": True,
            "official_holdout_executions": 0,
            "provider_calls": 0,
            "deterministic_json": True,
            "development_failure_map": map_hashes,
            "development_calibration_freeze": "DEVELOPMENT_CALIBRATION_FREEZE.json",
        }
    )
    write(PACKAGE / "VALIDATION.json", validation)

    case_review_paths = [
        PACKAGE / next(case["category"] for case in manifest["cases"] if case["case_id"] == case_id) / case_id / "review_sheet.json"
        for case_id in CASE_IDS
    ]
    case_hash_paths = [path.parent / "hashes.json" for path in case_review_paths]
    freeze_paths = [
        PACKAGE / "FULL_AI_ASSISTED_LEDGER.json",
        *(PACKAGE / path for path in calibration_files if path != "DEVELOPMENT_CALIBRATION_FREEZE.json"),
        *case_review_paths,
        *case_hash_paths,
    ]
    calibration_artifact_hashes = {
        str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
        for path in sorted(freeze_paths)
    }
    freeze = {
        "schema_version": "enterprise-insight-v2-development-calibration-freeze/1.0.0",
        "benchmark_schema": RUBRIC_VERSION,
        "dataset_sha256": DATASET_SHA256,
        "cutoff": "2026-09-05",
        "selected_development_case_ids": CASE_IDS,
        "human_review_completion_status": "COMPLETED",
        "human_review_task_count": 87,
        "human_review_finalized_count": 87,
        "reviewer_identity": REVIEWER,
        "required_unit_result": "1/18",
        "required_unit_satisfied": 1,
        "required_unit_not_satisfied": 17,
        "calibration_artifact_hashes": calibration_artifact_hashes,
        "full_ai_assisted_ledger_sha256": before["full_ledger"],
        "benchmark_rubric_sha256": before["rubric"],
        "current_source_commit": source_commit_value,
        "source_commit": source_commit_value,
        "frozen_timestamp": timestamp,
        "official_holdout_executions": 0,
        "provider_calls": 0,
        "holdout_status": "UNEXECUTED_UNVIEWED_UNANNOTATED",
        "notes": [
            "Human decisions are written to the bounded calibration layers and linked review-sheet records.",
            "FULL_AI_ASSISTED_LEDGER.json is preserved as AI-assisted and is not final gold.",
            "This freeze does not modify Agent runtime behavior or implement utility-correction work packages.",
        ],
    }
    write(PACKAGE / "DEVELOPMENT_CALIBRATION_FREEZE.json", freeze)

    after = {
        "full_ledger": digest(PACKAGE / "FULL_AI_ASSISTED_LEDGER.json"),
        "dataset": digest(DATASET),
        "rubric": digest(RUBRIC),
        "v2_runtime_files": {
            str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
            for path in sorted((ROOT / "gpt_researcher").rglob("*.py"))
        },
    }
    assert before == after
    assert digest(DATASET) == DATASET_SHA256
    assert digest(PACKAGE / "FULL_AI_ASSISTED_LEDGER.json") == before["full_ledger"]
    assert len(failure_map["records"]) == 18
    assert Counter(record["final_human_decision"] for record in failure_map["records"]) == Counter({"SATISFIED": 1, "NOT_SATISFIED": 17})
    return {
        "status": "PASSED",
        "timestamp": timestamp,
        "reviewer": REVIEWER,
        "human_review_tasks_finalized": 87,
        "required_unit_result": "1/18",
        "full_ai_assisted_ledger_sha256": before["full_ledger"],
        "dataset_sha256": before["dataset"],
        "rubric_sha256": before["rubric"],
        "agent_runtime_files_checked": len(before["v2_runtime_files"]),
        "provider_calls": 0,
        "official_holdout_executions": 0,
        "failure_map_records": 18,
        "freeze_artifact_sha256": digest(PACKAGE / "DEVELOPMENT_CALIBRATION_FREEZE.json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timestamp", required=True, help="UTC ISO-8601 timestamp for the freeze")
    args = parser.parse_args()
    parsed = datetime.fromisoformat(args.timestamp.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    print(json.dumps(finalize(args.timestamp), ensure_ascii=False, sort_keys=True))
