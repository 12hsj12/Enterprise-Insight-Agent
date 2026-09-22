"""Pure-offline replay of saved Enterprise V2 executions through unit audit.

No researcher, retriever, provider, or LLM entry point is imported or called.
The script consumes only saved ``execution.json`` and ``writer_draft.md``
artifacts, then writes replay reports plus a machine-readable acceptance summary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gpt_researcher.enterprise.integration import IntegratedExecution, render_report
from gpt_researcher.enterprise.unit_audit import is_recommendation, split_markdown_audit_units


CASES = ("EIV2_CC_001", "EIV2_CR_003", "EIV2_ED_002")
INTERNAL_LABELS = ("VERIFIED_FACT", "LIMITED_EVIDENCE", "AI_INFERENCE", "UNRESOLVED")


def _single(case_dir: Path, name: str) -> Path:
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


def replay_case(case_dir: Path, output_dir: Path) -> dict:
    execution_payload = json.loads(_single(case_dir, "execution.json").read_text(encoding="utf-8"))
    execution = IntegratedExecution.model_validate(execution_payload["execution"])
    writer_draft = _single(case_dir, "writer_draft.md").read_text(encoding="utf-8")
    report = render_report(execution, writer_draft=writer_draft)

    case_output = output_dir / case_dir.name
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
    recommendation_bypass = sum(
        record.recommendation
        and (record.action == "keep" or (record.action == "replace" and not record.inference_id))
        and record.state.value not in {"OMIT", "UNRESOLVED"}
        for record in records
    )
    stronger_wording_bypass = sum(
        record.state.value in {"LIMITED", "OMIT", "UNRESOLVED"}
        and record.claim_bearing
        # Ignore short labels that can legitimately recur in another audited
        # unit (for example a table cell containing "Provisioned Throughput").
        and len(original_units[record.unit_id].text.strip()) >= 40
        and original_units[record.unit_id].text.strip() in report
        for record in records
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
        "case_id": case_dir.name,
        "offline_only": True,
        "writer_draft_bytes": len(writer_draft.encode("utf-8")),
        "report_bytes": len(report.encode("utf-8")),
        "report_to_draft_ratio": round(len(report) / max(1, len(writer_draft)), 4),
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
        "internal_label_count": sum(report.count(label) for label in INTERNAL_LABELS),
        "high_risk_unaudited_unit_count": summary["high_risk_unaudited_unit_count"],
        "recommendation_bypass_count": recommendation_bypass,
        "causal_bypass_count": causal_bypass,
        "table_numeric_uncovered_count": table_numeric_uncovered,
        "substring_fragment_deletion_count": summary["substring_fragment_deletion_count"],
        "claim_bearing_unit_count": summary["claim_bearing_unit_count"],
        "unit_audit_record_count": len(records),
        "premise_bound_recommendation_count": summary["premise_bound_recommendation_count"],
        "stronger_wording_bypass_count": stronger_wording_bypass,
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
    args = parser.parse_args()
    root = args.input.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = [replay_case(root / case_id, output) for case_id in CASES]
    acceptance = {
        "cases": results,
        "hard_checks": {
            "high_risk_unaudited_unit_zero": all(
                item["high_risk_unaudited_unit_count"] == 0 for item in results
            ),
            "recommendation_bypass_zero": all(
                item["recommendation_bypass_count"] == 0 for item in results
            ),
            "substring_fragment_deletion_zero": all(
                item["substring_fragment_deletion_count"] == 0 for item in results
            ),
            "tables_well_formed": all(
                item["malformed_table_count"] == 0 for item in results
            ),
            "no_dangling_fragments": all(
                item["dangling_fragment_count"] == 0 for item in results
            ),
            "primary_titles_preserved": all(item["primary_title_preserved"] for item in results),
            "heading_framework_preserved": all(
                item["heading_count_preserved"]
                and item["non_recommendation_headings_preserved"]
                for item in results
            ),
            "comparison_tables_preserved": all(
                item["table_separator_count_preserved"] for item in results
            ),
            "no_internal_labels": all(item["internal_label_count"] == 0 for item in results),
            "grounding_stronger_wording_protected": all(
                item["stronger_wording_bypass_count"] == 0 for item in results
            ),
            "causal_bypass_zero": all(item["causal_bypass_count"] == 0 for item in results),
            "table_numeric_units_covered": all(
                item["table_numeric_uncovered_count"] == 0 for item in results
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
