"""Pure-offline replay of saved Enterprise V2 executions through unit audit.

No researcher, retriever, provider, or LLM entry point is imported or called.
The script consumes only saved ``execution.json`` and ``writer_draft.md``
artifacts, then writes replay reports plus a machine-readable acceptance summary.
"""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gpt_researcher.enterprise.integration import IntegratedExecution, render_report
from gpt_researcher.enterprise.unit_audit import (
    AuditUnitType, is_recommendation, markdown_visible_text,
    split_markdown_audit_units,
)


CASES = ("EIV2_CC_001", "EIV2_CR_003", "EIV2_ED_002")
INTERNAL_LABELS = (
    "VERIFIED", "LIMITED", "AI_INFERENCE", "AI_ANALYSIS", "UNRESOLVED",
    "premise strength",
)
NON_DESTRUCTIVE_BASELINE_RETENTION = {
    "EIV2_CC_001": 1.0,
    "EIV2_CR_003": 0.9995,
    "EIV2_ED_002": 0.9999,
}


def _single(case_dir: Path, name: str) -> Path:
    direct = case_dir / name
    if direct.is_file():
        return direct
    matches = list((case_dir / "enterprise").glob(f"*/{name}"))
    if len(matches) != 1:
        raise ValueError(f"Expected one {name} below {case_dir}, found {len(matches)}")
    return matches[0]


def _headings(text: str) -> list[str]:
    return re.findall(r"(?m)^#{1,6}\s+.+$", text)


def _table_shape_errors(text: str) -> int:
    errors = 0
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^\s*\|?\s*:?-{3,}", line) or "|" not in line:
            continue
        if index == 0:
            errors += 1
            continue
        expected = lines[index - 1].count("|")
        row = index + 1
        while row < len(lines) and "|" in lines[row] and lines[row].strip():
            if lines[row].count("|") != expected:
                errors += 1
            row += 1
    return errors


def _dangling_fragment_count(text: str) -> int:
    patterns = (
        r"(?m)^\s*[,;，；]\s+",
        r"(?m)^\s*(?:and|or|but)\s*[,.!?。！？]",
        r"[,;，；]\s*[,;，；]",
        r"\b(?:and|or|but)\s+(?=\n\s*\n|#{1,6}\s|$)",
    )
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns)


def _recommendation_payload(text: str, unit_type: AuditUnitType) -> str:
    payload = text.strip()
    if unit_type is AuditUnitType.LIST_ITEM:
        payload = re.sub(r"^\s*(?:[-*+] |\d+[.)] )", "", payload)
    if unit_type is AuditUnitType.HEADING:
        payload = re.sub(r"^#{1,6}\s+", "", payload)
    return markdown_visible_text(payload)


def replay_case(case_dir: Path, output_dir: Path, *, case_id: str | None = None) -> dict:
    case_id = case_id or case_dir.name
    execution_payload = json.loads(_single(case_dir, "execution.json").read_text(encoding="utf-8"))
    execution = IntegratedExecution.model_validate(execution_payload["execution"])
    writer_draft = _single(case_dir, "writer_draft.md").read_text(encoding="utf-8")
    report = render_report(execution, writer_draft=writer_draft)

    case_output = output_dir / case_id
    case_output.mkdir(parents=True, exist_ok=True)
    (case_output / "report.md").write_text(report, encoding="utf-8")
    (case_output / "unit_audit.json").write_text(
        json.dumps(
            [record.model_dump(mode="json") for record in execution.unit_audit_records],
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    summary = execution.final_render_audit_summary
    records = execution.unit_audit_records
    original_units = {
        unit.unit_id: unit for unit in split_markdown_audit_units(writer_draft)
    }
    record_by_unit = {record.unit_id: record for record in records}
    original_headings = _headings(writer_draft)
    final_headings = _headings(report)
    original_h1 = [heading for heading in original_headings if heading.startswith("# ")]
    final_h1 = [heading for heading in final_headings if heading.startswith("# ")]
    original_recommendations = [
        unit for unit in original_units.values() if unit.recommendation
    ]
    visible_report = markdown_visible_text(report)
    retained_recommendations = [
        unit for unit in original_recommendations
        if _recommendation_payload(unit.text, unit.unit_type) in visible_report
    ]
    substantive_recommendations = [
        unit for unit in retained_recommendations
        if unit.unit_type is not AuditUnitType.HEADING
    ]
    selection_recommendations = [
        unit for unit in substantive_recommendations
        if re.search(
            r"\b(?:choose|select|default|stay\s+on|right\s+answer|recommended|"
            r"managed\s+service|pgvector|milvus|qdrant|elasticsearch|opensearch)\b|"
            r"(?:选择|选型|首选|优先|默认)",
            _recommendation_payload(unit.text, unit.unit_type),
            flags=re.IGNORECASE,
        )
    ]
    migration_recommendations = [
        unit for unit in substantive_recommendations
        if re.search(
            r"\b(?:migrat|switch|cutover|rollback|dual[- ]write|shadow)\w*\b|"
            r"(?:迁移|切换|回滚|双写)",
            _recommendation_payload(unit.text, unit.unit_type),
            flags=re.IGNORECASE,
        )
    ]
    retained_characters = sum(
        match.size
        for match in SequenceMatcher(
            None, writer_draft, report, autojunk=False,
        ).get_matching_blocks()
    )
    non_recommendation_headings = [
        heading for heading in original_headings
        if not is_recommendation(re.sub(r"^#{1,6}\s+", "", heading))
    ]
    table_numeric_uncovered = sum(
        unit.unit_type.value == "table_cell"
        and bool(re.search(r"\d", unit.text))
        and unit.unit_id not in record_by_unit
        for unit in original_units.values()
    )
    causal_bypass = sum(
        bool(re.search(
            r"\b(?:because|due to|causes?|leads? to|results? in|drives?|reduces?|"
            r"increases?)\b|(?:因为|由于|导致|因此|带来|降低|提高|增加)",
            unit.text,
            flags=re.IGNORECASE,
        ))
        and unit.claim_bearing
        and (
            unit.unit_id not in record_by_unit
            or (
                record_by_unit[unit.unit_id].action == "keep"
                and not record_by_unit[unit.unit_id].claim_ids
            )
        )
        for unit in original_units.values()
    )
    result = {
        "case_id": case_id,
        "offline_only": True,
        "writer_draft_bytes": len(writer_draft.encode("utf-8")),
        "report_bytes": len(report.encode("utf-8")),
        "report_to_draft_ratio": round(len(report) / max(1, len(writer_draft)), 4),
        "writer_body_retention_ratio": round(
            retained_characters / max(1, len(writer_draft)), 4
        ),
        "original_heading_count": len(original_headings),
        "final_heading_count": len(final_headings),
        "primary_title_preserved": original_h1 == final_h1,
        "heading_count_preserved": len(original_headings) == len(final_headings),
        "non_recommendation_headings_preserved": all(
            heading in final_headings for heading in non_recommendation_headings
        ),
        "table_separator_count_preserved": (
            len(re.findall(r"(?m)^\s*\|?\s*:?-{3,}.*\|", writer_draft))
            == len(re.findall(r"(?m)^\s*\|?\s*:?-{3,}.*\|", report))
        ),
        "malformed_table_count": _table_shape_errors(report),
        "dangling_fragment_count": _dangling_fragment_count(report),
        "internal_label_count": (
            sum(report.count(label) for label in INTERNAL_LABELS[:-1])
            + len(re.findall(
                re.escape(INTERNAL_LABELS[-1]), report, flags=re.IGNORECASE,
            ))
        ),
        "high_risk_unaudited_unit_count": summary["high_risk_unaudited_unit_count"],
        "recommendation_bypass_count": summary["recommendation_bypass_count"],
        "original_recommendation_count": len(original_recommendations),
        "retained_recommendation_count": len(retained_recommendations),
        "substantive_recommendation_count": len(substantive_recommendations),
        "selection_recommendation_count": len(selection_recommendations),
        "migration_recommendation_count": len(migration_recommendations),
        "surviving_inference_count": len(execution.surviving_inferences),
        "recommendation_deletion_count": summary["recommendation_deletion_count"],
        "circular_premise_count": summary["circular_premise_count"],
        "already_audited_premise_repeated_gate_count": summary[
            "already_audited_premise_repeated_gate_count"
        ],
        "recommendation_new_high_risk_fact_count": summary[
            "recommendation_new_high_risk_fact_count"
        ],
        "recommendation_new_high_risk_fact_qualified_count": summary[
            "recommendation_new_high_risk_fact_qualified_count"
        ],
        "recommendation_repeated_disclaimer_count": summary[
            "recommendation_repeated_disclaimer_count"
        ],
        "causal_bypass_count": causal_bypass,
        "table_numeric_uncovered_count": table_numeric_uncovered,
        "substring_fragment_deletion_count": summary["substring_fragment_deletion_count"],
        "fail_safe_deletion_count": summary["fail_safe_deletion_count"],
        "claim_reconstruction_count": summary["claim_reconstruction_count"],
        "destructive_unit_deletion_count": summary["destructive_unit_deletion_count"],
        "omit_action_count": sum(record.action == "omit" for record in records),
        "claim_bearing_unit_count": summary["claim_bearing_unit_count"],
        "unit_audit_record_count": len(records),
        "premise_bound_recommendation_count": summary["premise_bound_recommendation_count"],
        "unsupported_stronger_verified_count": summary[
            "unsupported_stronger_verified_count"
        ],
        "cr_source_frame_preserved": (
            case_id != "EIV2_CR_003"
            or (
                "Vendor-Reported" in report
                and "Third-Party Results" in report
                and "Artificial Analysis" in report
            )
        ),
        "meets_non_destructive_baseline": (
            round(retained_characters / max(1, len(writer_draft)), 4)
            >= NON_DESTRUCTIVE_BASELINE_RETENTION[case_id]
        ),
        "audit_summary": summary,
    }
    (case_output / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--case-dir", action="append", default=[], metavar="CASE_ID=PATH",
        help="Override one or more case locations with saved direct task directories.",
    )
    args = parser.parse_args()
    root = args.input.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    case_directories = {case_id: root / case_id for case_id in CASES}
    for value in args.case_dir:
        case_id, separator, path = value.partition("=")
        if not separator or case_id not in CASES or not path:
            parser.error("--case-dir must be one of EIV2_CC_001=PATH, EIV2_CR_003=PATH, EIV2_ED_002=PATH")
        case_directories[case_id] = Path(path).resolve()
    results = [
        replay_case(case_directories[case_id], output, case_id=case_id)
        for case_id in CASES
    ]
    by_case = {item["case_id"]: item for item in results}
    cc = by_case["EIV2_CC_001"]
    cr = by_case["EIV2_CR_003"]
    ed = by_case["EIV2_ED_002"]
    acceptance = {
        "cases": results,
        "hard_checks": {
            "gate_01_cc_body_comparison_tables_preserved": (
                cc["primary_title_preserved"]
                and cc["heading_count_preserved"]
                and cc["table_separator_count_preserved"]
                and cc["malformed_table_count"] == 0
            ),
            "gate_02_cr_official_third_party_material_preserved": (
                cr["primary_title_preserved"]
                and cr["heading_count_preserved"]
                and cr["cr_source_frame_preserved"]
            ),
            "gate_03_ed_selection_and_migration_recommendations_present": (
                ed["selection_recommendation_count"] > 0
                and ed["migration_recommendation_count"] > 0
            ),
            "gate_04_ed_recommendations_survive_zero_inferences": (
                ed["surviving_inference_count"] != 0
                or ed["substantive_recommendation_count"] > 0
            ),
            "gate_05_recommendation_deletion_zero": all(
                item["recommendation_deletion_count"] == 0
                and item["retained_recommendation_count"]
                == item["original_recommendation_count"]
                for item in results
            ),
            "gate_06_no_new_high_risk_recommendation_bypass": all(
                item["recommendation_bypass_count"] == 0
                and item["recommendation_new_high_risk_fact_count"]
                == item["recommendation_new_high_risk_fact_qualified_count"]
                for item in results
            ),
            "gate_07_circular_premise_zero": all(
                item["circular_premise_count"] == 0 for item in results
            ),
            "gate_08_repeated_premise_gate_zero": all(
                item["already_audited_premise_repeated_gate_count"] == 0
                for item in results
            ),
            "gate_09_fail_safe_deletion_zero": all(
                item["fail_safe_deletion_count"] == 0 for item in results
            ),
            "gate_10_claim_reconstruction_zero": all(
                item["claim_reconstruction_count"] == 0 for item in results
            ),
            "gate_11_substring_deletion_zero": all(
                item["substring_fragment_deletion_count"] == 0 for item in results
            ),
            "gate_12_no_broken_sentence_or_table": all(
                item["malformed_table_count"] == 0
                and item["dangling_fragment_count"] == 0
                and item["destructive_unit_deletion_count"] == 0
                and item["omit_action_count"] == 0
                for item in results
            ),
            "gate_13_unsupported_stronger_verified_zero": all(
                item["unsupported_stronger_verified_count"] == 0 for item in results
            ),
            "gate_14_user_visible_internal_labels_zero": all(
                item["internal_label_count"] == 0 for item in results
            ),
            "gate_15_repeated_recommendation_disclaimer_zero": all(
                item["recommendation_repeated_disclaimer_count"] == 0
                for item in results
            ),
            "gate_16_report_completeness_not_below_baseline": all(
                item["meets_non_destructive_baseline"]
                and item["primary_title_preserved"]
                and item["heading_count_preserved"]
                and item["table_separator_count_preserved"]
                for item in results
            ),
        },
    }
    acceptance["passed"] = all(acceptance["hard_checks"].values())
    (output / "acceptance.json").write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(acceptance, ensure_ascii=False, indent=2))
    return 0 if acceptance["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
