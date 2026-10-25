"""Offline replay of Batch 2 metadata logic over saved six-case evidence."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gpt_researcher.evidence.metadata import enrich_page_metadata
from gpt_researcher.evidence.models import Evidence, SourceRole


def _known_publisher(item: dict) -> bool:
    return bool(item.get("publisher") or item.get("source_organization") or item.get("source_owner"))


def _metrics(items: list[dict]) -> dict[str, int]:
    known_publishers = sum(_known_publisher(item) for item in items)
    known_dates = sum(bool(item.get("publication_date")) for item in items)
    first_party = sum(item.get("source_role") == SourceRole.FIRST_PARTY.value for item in items)
    return {
        "evidence_count": len(items),
        "known_publisher": known_publishers,
        "unknown_publisher": len(items) - known_publishers,
        "known_publication_date": known_dates,
        "unknown_publication_date": len(items) - known_dates,
        "freshness_computable": known_dates,
        "first_party_identifiable": first_party,
    }


def replay(input_directory: Path, *, reference_date: date) -> dict:
    selected_files = sorted(input_directory.glob("*/*/selected.json"))
    if len(selected_files) != 6:
        raise ValueError(f"Expected six saved calibration cases, found {len(selected_files)}")
    before = []
    after = []
    case_counts = {}
    for path in selected_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["evidences"]
        before.extend(rows)
        enriched_rows = []
        for row in rows:
            page = dict(row)
            # Replay each saved chunk exactly as stored. Because page offsets
            # and original HTML are absent, this is a conservative lower bound.
            page["raw_content"] = row.get("content", "")
            enriched = enrich_page_metadata(page)
            enriched.pop("raw_content", None)
            # Model validation proves old/new serialized records are compatible.
            enriched = Evidence.model_validate(enriched).model_dump(mode="json")
            enriched_rows.append(enriched)
        after.extend(enriched_rows)
        case_counts[payload["case_id"]] = {
            "before": _metrics(rows),
            "after": _metrics(enriched_rows),
        }

    before_metrics = _metrics(before)
    after_metrics = _metrics(after)
    dated = [date.fromisoformat(item["publication_date"]) for item in after
             if item.get("publication_date")]
    return {
        "schema_version": "v2-source-metadata-replay-1",
        "input": {
            "directory": input_directory.as_posix(),
            "case_count": len(selected_files),
            "saved_evidence_only": True,
            "live_web": False,
        },
        "reference_date": reference_date.isoformat(),
        "freshness_diagnostic_window_days": 180,
        "before": before_metrics,
        "after": after_metrics,
        "qualification_impact": {
            "identity_newly_usable": after_metrics["known_publisher"] - before_metrics["known_publisher"],
            "freshness_newly_computable": after_metrics["freshness_computable"] - before_metrics["freshness_computable"],
            "first_party_newly_identifiable": after_metrics["first_party_identifiable"] - before_metrics["first_party_identifiable"],
            "verified_within_180_days": sum(
                0 <= (reference_date - value).days <= 180 for value in dated
            ),
            "verified_older_than_180_days": sum(
                (reference_date - value).days > 180 for value in dated
            ),
        },
        "by_case": case_counts,
        "runtime_calls": {
            "provider": 0,
            "search": 0,
            "development": 0,
            "holdout": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "docs" / "v2" / "calibration" / "v2.2.0",
    )
    parser.add_argument("--reference-date", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = replay(args.input, reference_date=args.reference_date)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
