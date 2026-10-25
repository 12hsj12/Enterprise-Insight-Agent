"""Offline replay of the final six saved artifacts for semantic risk closure.

This command performs no network or provider calls.  The historical fixture is
test-only expected routing data for previously observed misses; all other units
retain an explicit ordinary/analysis/structural classification, while the
production deterministic detector remains unioned by the renderer.
"""

from __future__ import annotations

import argparse
from datetime import date
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gpt_researcher.enterprise.integration import IntegratedExecution, render_report
from gpt_researcher.enterprise.semantic_risk import (
    SemanticRiskAssignment,
    SemanticRiskCategory,
    SemanticRiskRouting,
    is_structural_unit,
)
from gpt_researcher.enterprise.unit_audit import (
    AuditUnitType,
    alignment_text,
    split_markdown_audit_units,
)


EXPECTED_CASES = (
    "EIV2_FV_001",
    "EIV2_TC_001",
    "EIV2_CC_001",
    "EIV2_TM_003",
    "EIV2_CR_003",
    "EIV2_ED_002",
)
INTERNAL_LABELS = ("VERIFIED_FACT", "LIMITED_EVIDENCE", "UNRESOLVED", "AI_INFERENCE")


def _routing_for_case(case_id: str, draft: str, historical: list[dict]) -> tuple[
    SemanticRiskRouting, list[str]
]:
    units = split_markdown_audit_units(draft)
    matches: dict[str, SemanticRiskCategory] = {}
    missing_needles = []
    for item in historical:
        if item["case_id"] != case_id:
            continue
        matching = [unit for unit in units if item["contains"] in unit.text]
        if len(matching) != 1:
            missing_needles.append(item["contains"])
            continue
        matches[matching[0].unit_id] = SemanticRiskCategory(item["category"])
    assignments = []
    for unit in units:
        if unit.unit_id in matches:
            category = matches[unit.unit_id]
        elif is_structural_unit(unit):
            category = SemanticRiskCategory.STRUCTURAL_NONCLAIM
        elif unit.recommendation:
            category = SemanticRiskCategory.ANALYSIS_RECOMMENDATION
        else:
            category = SemanticRiskCategory.ORDINARY_CONTEXT
        assignments.append(SemanticRiskAssignment(
            unit_id=unit.unit_id,
            category=category,
        ))
    return SemanticRiskRouting(status="complete", assignments=assignments), missing_needles


def _table_shape_is_preserved(draft: str, report: str) -> bool:
    draft_separators = re.findall(r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$", draft)
    report_separators = re.findall(r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$", report)
    if len(draft_separators) != len(report_separators):
        return False
    return all(
        line.count("|") >= 2
        for line in report.splitlines()
        if re.match(r"^\s*\|", line)
    )


def _preservation_text(value: str) -> str:
    return alignment_text(html.unescape(value).replace("\\", ""))


def _preserved_unit_text(unit) -> str:
    value = unit.text
    if unit.unit_type is AuditUnitType.LIST_ITEM:
        value = re.sub(r"^\s*(?:[-*+] |\d+[.)] )", "", value)
    return _preservation_text(value)


def _case_replay(run: dict, historical: list[dict]) -> dict:
    case_id = run["case_id"]
    execution_path = Path(run["execution"])
    artifact_dir = execution_path.parent
    draft_path = artifact_dir / "writer_draft.md"
    draft = draft_path.read_text(encoding="utf-8")
    payload = json.loads(execution_path.read_text(encoding="utf-8"))
    execution = IntegratedExecution.model_validate(payload["execution"])
    routing, missing_needles = _routing_for_case(case_id, draft, historical)
    execution = execution.model_copy(update={"semantic_risk_routing": routing})
    replayed = render_report(execution, writer_draft=draft)
    units = split_markdown_audit_units(draft)
    summary = execution.final_render_audit_summary
    route_categories = routing.category_by_unit()
    expected_units = [
        unit for unit in units
        if any(
            item["case_id"] == case_id and item["contains"] in unit.text
            for item in historical
        )
    ]
    records = {record.unit_id: record for record in execution.unit_audit_records}
    missed_expected = [
        unit.unit_id for unit in expected_units
        if not records.get(unit.unit_id)
        or "OUTSIDE_HIGH_RISK_GATE" in records[unit.unit_id].reason_codes
        or route_categories.get(unit.unit_id) in {
            SemanticRiskCategory.ORDINARY_CONTEXT,
            SemanticRiskCategory.ANALYSIS_RECOMMENDATION,
            SemanticRiskCategory.STRUCTURAL_NONCLAIM,
        }
    ]
    metadata = {item.evidence_id: item for item in execution.audit_metadata}
    cutoff = date.fromisoformat(run.get("request", {}).get("cutoff_date", "2026-09-05"))
    post_cutoff_ids = {
        evidence_id for evidence_id, item in metadata.items()
        if item.publication_date is not None and item.publication_date > cutoff
    }
    post_cutoff_strong_support = sum(
        bool(set(record.cited_evidence_ids) & post_cutoff_ids)
        for record in execution.evidence_context.generated_claim_records
    )
    headings = re.findall(r"(?m)^#{1,6}\s+.+$", draft)
    aligned_report = _preservation_text(replayed)
    unpreserved_units = [
        unit for unit in units
        if _preserved_unit_text(unit)
        and _preserved_unit_text(unit) not in aligned_report
    ]
    preserved_units = len(units) - len(unpreserved_units)
    recommendation_units = [unit for unit in units if unit.recommendation]
    recommendation_records = [
        record for record in execution.unit_audit_records if record.recommendation
    ]
    checks = {
        "known_bypasses_captured": not missing_needles and not missed_expected,
        "post_cutoff_strong_support_zero": post_cutoff_strong_support == 0,
        "factual_high_risk_bypass_zero": summary["high_risk_bypass_units"] == 0,
        "report_reconstruction_zero": summary["claim_reconstruction_count"] == 0,
        "destructive_deletion_zero": summary["destructive_unit_deletion_count"] == 0,
        "substring_deletion_zero": summary["substring_fragment_deletion_count"] == 0,
        "broken_prose_table_zero": _table_shape_is_preserved(draft, replayed),
        "recommendation_regression_zero": (
            len(recommendation_units) == len(recommendation_records)
            and summary["recommendation_deletion_count"] == 0
        ),
        "circular_recommendation_zero": summary["circular_premise_count"] == 0,
        "repeated_audit_zero": summary["already_audited_premise_repeated_gate_count"] == 0,
        "internal_label_pollution_zero": not any(label in replayed for label in INTERNAL_LABELS),
        "unsupported_stronger_final_statement_zero": summary[
            "unsupported_stronger_verified_count"
        ] == 0,
        "report_structure_preserved": all(heading in replayed for heading in headings),
        "report_preservation_full": preserved_units == len(units),
    }
    return {
        "case_id": case_id,
        "coverage": {
            key: summary[key] for key in (
                "total_content_units",
                "structural_units",
                "recommendation_units",
                "objective_candidate_units",
                "deterministic_high_risk_units",
                "semantic_high_risk_units",
                "union_high_risk_units",
                "audited_high_risk_units",
                "unrouted_candidate_units",
                "high_risk_bypass_units",
            )
        },
        "historical_expected_units": len(expected_units),
        "historical_false_negatives": len(missed_expected) + len(missing_needles),
        "post_cutoff_strong_support": post_cutoff_strong_support,
        "preserved_units": preserved_units,
        "total_units": len(units),
        "unpreserved_unit_previews": [
            unit.text[:160] for unit in unpreserved_units
        ],
        "checks": checks,
        "passed": all(checks.values()),
    }


def replay(base: Path, fixture: Path) -> dict:
    runs = json.loads((base / "runs.json").read_text(encoding="utf-8"))
    by_case = {run["case_id"]: run for run in runs}
    missing_cases = [case_id for case_id in EXPECTED_CASES if case_id not in by_case]
    if missing_cases:
        raise ValueError(f"Missing replay cases: {missing_cases}")
    historical = json.loads(fixture.read_text(encoding="utf-8"))
    cases = [_case_replay(by_case[case_id], historical) for case_id in EXPECTED_CASES]
    coverage_keys = cases[0]["coverage"]
    aggregate = {
        key: sum(case["coverage"][key] for case in cases)
        for key in coverage_keys
    }
    return {
        "mode": "offline_saved_artifact_replay",
        "provider_calls": 0,
        "cases": cases,
        "coverage": aggregate,
        "historical_false_negatives": sum(
            case["historical_false_negatives"] for case in cases
        ),
        "passed": all(case["passed"] for case in cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "semantic_risk_historical.json",
    )
    args = parser.parse_args()
    result = replay(args.base.resolve(), args.fixture.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
