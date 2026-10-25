"""Offline product-quality replay over the latest six saved live artifacts.

No provider, search, crawl, Writer, holdout, or benchmark call is made.  Saved
Gate/Grounding records are rendered through the answer-critical boundary.
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

from gpt_researcher.enterprise.answer_critical import (
    AnswerCriticalAssignment,
    AnswerCriticalReason,
    AnswerCriticalReview,
    RecommendationPremiseReview,
)
from gpt_researcher.enterprise.integration import IntegratedExecution, render_report
from gpt_researcher.enterprise.requirements import RequirementType
from gpt_researcher.enterprise.unit_audit import (
    AuditUnitType,
    alignment_text,
    find_claim_unit,
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
LIMITATION_PHRASES = (
    "Current evidence does not establish the following claim(s)",
    "The cited sources support the following claim(s)",
    "Sources conflict on the following claim(s)",
)


def _preservation_text(value: str) -> str:
    return alignment_text(html.unescape(value).replace("\\", ""))


def _preserved_unit_text(unit) -> str:
    value = unit.text
    if unit.unit_type is AuditUnitType.LIST_ITEM:
        value = re.sub(r"^\s*(?:[-*+] |\d+[.)] )", "", value)
    return _preservation_text(value)


def _limitation_repeat_count(report: str) -> int:
    """Count repeats only within one paragraph or one Markdown table row."""

    repeats = 0
    prose: list[str] = []

    def flush() -> None:
        nonlocal repeats
        block = " ".join(prose)
        repeats += sum(max(0, block.count(phrase) - 1) for phrase in LIMITATION_PHRASES)
        prose.clear()

    for line in report.splitlines():
        if line.lstrip().startswith("|"):
            flush()
            repeats += sum(max(0, line.count(phrase) - 1) for phrase in LIMITATION_PHRASES)
        elif not line.strip() or line.lstrip().startswith("#"):
            flush()
        else:
            prose.append(line)
    flush()
    return repeats


def _table_shape_is_preserved(draft: str, report: str) -> bool:
    draft_separators = re.findall(r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$", draft)
    report_separators = re.findall(r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$", report)
    return len(draft_separators) == len(report_separators) and all(
        line.count("|") >= 2
        for line in report.splitlines()
        if line.lstrip().startswith("|")
    )


def _review_from_saved_execution(
    case_id: str,
    draft: str,
    execution: IntegratedExecution,
    fixture: list[dict],
) -> tuple[AnswerCriticalReview, list[str]]:
    units = split_markdown_audit_units(draft)
    assignments: dict[str, dict[str, set[str]]] = {}
    claim_units: dict[str, str] = {}

    def add(unit_id: str, reason: AnswerCriticalReason, requirement_ids=()):
        item = assignments.setdefault(unit_id, {"reasons": set(), "requirements": set()})
        item["reasons"].add(reason.value)
        item["requirements"].update(requirement_ids)

    requirement_by_id = {
        item.requirement_id: item for item in execution.requirements
    }
    for item in execution.claim_inputs:
        unit = next((unit for unit in units if unit.unit_id == item.unit_id), None)
        if unit is None:
            unit = find_claim_unit(units, item.claim.normalized_text)
        if unit is None:
            continue
        claim_units[item.claim.claim_id] = unit.unit_id
        reason = AnswerCriticalReason.REQUIREMENT_ANSWER
        requirement = requirement_by_id.get(item.requirement_id or "")
        if requirement and requirement.requirement_type is RequirementType.COMPARATIVE:
            reason = AnswerCriticalReason.COMPARISON_DIFFERENTIATOR
        add(unit.unit_id, reason, (item.requirement_id,) if item.requirement_id else ())

    missing_needles = []
    for item in fixture:
        if item["case_id"] != case_id:
            continue
        matches = [unit for unit in units if item["contains"] in unit.text]
        if len(matches) != 1:
            missing_needles.append(item["contains"])
            continue
        add(
            matches[0].unit_id,
            AnswerCriticalReason(item["reason"]),
            item.get("requirement_ids", ()),
        )

    recommendation_units = [unit for unit in units if unit.recommendation]
    recommendation_requirements = [
        item.requirement_id for item in execution.requirements
        if item.requirement_type is RequirementType.RECOMMENDATION
    ]
    if recommendation_units:
        for requirement_id in recommendation_requirements:
            add(
                recommendation_units[0].unit_id,
                AnswerCriticalReason.EXECUTIVE_DECISION,
                (requirement_id,),
            )

    premise_ids = tuple(dict.fromkeys(
        claim_units[claim_id]
        for inference in execution.surviving_inferences
        for claim_id in inference.premise_claim_ids
        if claim_id in claim_units
    ))
    recommendations = tuple(
        RecommendationPremiseReview(
            unit_id=unit.unit_id,
            premise_unit_ids=tuple(
                item for item in premise_ids
                if item not in {recommendation.unit_id for recommendation in recommendation_units}
            ),
            has_inline_factual_premise=unit.unit_id in assignments,
        )
        for unit in recommendation_units
    )
    by_id = {unit.unit_id: unit for unit in units}
    review = AnswerCriticalReview(
        status="complete",
        assignments=tuple(
            AnswerCriticalAssignment(
                unit_id=unit_id,
                reasons=tuple(AnswerCriticalReason(value) for value in sorted(data["reasons"])),
                requirement_ids=tuple(sorted(data["requirements"])),
            )
            for unit_id, data in sorted(
                assignments.items(), key=lambda pair: by_id[pair[0]].ordinal,
            )
        ),
        recommendations=recommendations,
    )
    return review, missing_needles


def _case_replay(run: dict, fixture: list[dict], output: Path | None) -> dict:
    case_id = run["case_id"]
    execution_path = Path(run["execution"])
    draft = (execution_path.parent / "writer_draft.md").read_text(encoding="utf-8")
    payload = json.loads(execution_path.read_text(encoding="utf-8"))
    execution = IntegratedExecution.model_validate(payload["execution"])
    review, missing_needles = _review_from_saved_execution(
        case_id, draft, execution, fixture,
    )
    execution = execution.model_copy(update={"answer_critical_review": review})
    report = render_report(execution, writer_draft=draft)
    if output is not None:
        case_dir = output / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "report.md").write_text(report, encoding="utf-8")
        (case_dir / "summary.json").write_text(json.dumps({
            "answer_critical_review": review.model_dump(mode="json"),
            "final_render_audit_summary": execution.final_render_audit_summary,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    units = split_markdown_audit_units(draft)
    aligned_report = _preservation_text(report)
    preserved = sum(
        not _preserved_unit_text(unit)
        or _preserved_unit_text(unit) in aligned_report
        for unit in units
    )
    headings = re.findall(r"(?m)^#{1,6}\s+.+$", draft)
    records = {item.unit_id: item for item in execution.unit_audit_records}
    critical_records = [records[item.unit_id] for item in review.assignments]
    metadata = {item.evidence_id: item for item in execution.audit_metadata}
    cutoff = date.fromisoformat(run.get("request", {}).get("cutoff_date", "2026-09-05"))
    post_cutoff = {
        evidence_id for evidence_id, item in metadata.items()
        if item.publication_date is not None and item.publication_date > cutoff
    }
    critical_claim_ids = {
        claim_id for record in critical_records for claim_id in record.claim_ids
    }
    post_cutoff_critical_strong = sum(
        record.claim_id in critical_claim_ids
        and bool(set(record.cited_evidence_ids) & post_cutoff)
        for record in execution.evidence_context.generated_claim_records
    )
    recommendation_records = [item for item in execution.unit_audit_records if item.recommendation]
    limitation_repeats = _limitation_repeat_count(report)
    summary = execution.final_render_audit_summary
    checks = {
        "task_completion": summary["answer_critical_mapped_requirement_count"]
        == summary["answer_critical_requirement_count"],
        "report_completeness": preserved == len(units),
        "answer_critical_claim_coverage": summary["answer_critical_reviewed_units"]
        == summary["answer_critical_units"],
        "answer_critical_unsupported_strong_claims_zero": summary[
            "answer_critical_unsupported_strong_claims"
        ] == 0,
        "recommendation_usability": (
            len(recommendation_records) == len(review.recommendations)
            and summary["recommendation_deletion_count"] == 0
        ),
        "readability": (
            not any(label in report for label in INTERNAL_LABELS)
            and not re.search(r"\bev_[0-9a-f]{8,}\b", report)
            and limitation_repeats == 0
        ),
        "runtime_stability": (
            summary["answer_critical_review_provider_errors"] == 0
            and not missing_needles
        ),
        "structure_preserved": all(heading in report for heading in headings),
        "table_shape_preserved": _table_shape_is_preserved(draft, report),
        "post_cutoff_critical_strong_support_zero": post_cutoff_critical_strong == 0,
        "no_repeated_gate": summary["already_audited_premise_repeated_gate_count"] == 0,
        "no_destructive_reconstruction": (
            summary["destructive_unit_deletion_count"] == 0
            and summary["claim_reconstruction_count"] == 0
        ),
    }
    return {
        "case_id": case_id,
        "metrics": {
            "task_completion": checks["task_completion"],
            "report_completeness": preserved / len(units) if units else 1.0,
            "answer_critical_claim_coverage": (
                summary["answer_critical_reviewed_units"]
                / summary["answer_critical_units"]
                if summary["answer_critical_units"] else 1.0
            ),
            "answer_critical_unsupported_strong_claims": summary[
                "answer_critical_unsupported_strong_claims"
            ],
            "recommendation_units_retained": len(recommendation_records),
            "readability_limitation_repeats": limitation_repeats,
            "runtime_provider_errors": summary["answer_critical_review_provider_errors"],
            "strict_ru_diagnostic": {
                "deterministic_high_risk_units": summary["deterministic_high_risk_units"],
                "semantic_high_risk_units": summary["semantic_high_risk_units"],
            },
        },
        "post_cutoff_critical_strong_support": post_cutoff_critical_strong,
        "checks": checks,
        "passed": all(checks.values()),
    }


def replay(base: Path, fixture_path: Path, output: Path | None = None) -> dict:
    runs = json.loads((base / "runs.json").read_text(encoding="utf-8"))
    by_case = {item["case_id"]: item for item in runs}
    missing = [case_id for case_id in EXPECTED_CASES if case_id not in by_case]
    if missing:
        raise ValueError(f"Missing replay cases: {missing}")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = [_case_replay(by_case[case_id], fixture, output) for case_id in EXPECTED_CASES]
    return {
        "mode": "offline_answer_critical_product_replay",
        "provider_calls": 0,
        "search_calls": 0,
        "holdout_calls": 0,
        "cases": cases,
        "aggregate": {
            "reports": len(cases),
            "reports_passed": sum(item["passed"] for item in cases),
            "answer_critical_unsupported_strong_claims": sum(
                item["metrics"]["answer_critical_unsupported_strong_claims"]
                for item in cases
            ),
            "recommendation_units_retained": sum(
                item["metrics"]["recommendation_units_retained"] for item in cases
            ),
        },
        "passed": all(item["passed"] for item in cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument(
        "--fixture", type=Path,
        default=Path(__file__).parent / "fixtures" / "product_quality_critical_units.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = replay(
        args.base.resolve(), args.fixture.resolve(),
        args.output.resolve() if args.output else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
