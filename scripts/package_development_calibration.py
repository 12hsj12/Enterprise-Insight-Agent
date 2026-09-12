"""Assemble saved six-case materials and explicit AI recommendations; no provider calls."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_development_calibration import IDS, PACKAGE, DATASET_SHA, preflight, write
from gpt_researcher.enterprise.calibration_capture import sha256

RUBRIC = "enterprise-insight-bench-v2/2.2.0"
SECTIONS = ("claim_segmentation", "citation_support", "required_unit", "evidence_strength",
            "independence", "freshness", "high_risk")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def package(source, recommendations):
    cases = dict((case["id"], case) for case, _ in preflight())
    rules = read(PACKAGE / "FROZEN_RULE_REFERENCES.json")
    configuration = read(source / "configuration.json")
    write(PACKAGE / "RUN_CONFIGURATION.json", configuration)
    # This directory's eol=lf attribute prevents Windows checkout from changing
    # audited bytes. These are calibration sidecars, never the frozen dataset.
    for path in PACKAGE.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".json"):
            data = path.read_bytes()
            if b"\r\n" in data:
                path.write_bytes(data.replace(b"\r\n", b"\n"))
    runs = read(source / "runs.json")
    assert [run["case_id"] for run in runs] == list(IDS)
    queue, entries, counts, risks = [], [], Counter(), set()
    for run in runs:
        cid = run["case_id"]
        case = cases[cid]
        directory = PACKAGE / case["category"] / cid
        task = read(source / cid / "task.json")
        assert task["task_id"] == run["task_id"]
        result = task.get("result") or {}
        diagnostic = task.get("diagnostics") or {}
        write(directory / "diagnostics.json", diagnostic)
        assert not run["capture_errors"]
        refs = {}
        for name, original in {"candidate": source / cid / "candidate.json",
                               "selected": source / cid / "selected.json",
                               "scoring": source / cid / "scoring.json",
                               "task": source / cid / "task.json",
                               "report": Path(run["report"]) if run["report"] else None,
                               "execution": Path(run["execution"]) if run["execution"] else None,
                               "trace": Path(run["trace"]) if run["trace"] else None}.items():
            if original is None:
                refs[name] = {"path": None, "sha256": None, "reason": "explicit failed run"}
                continue
            assert original.is_file()
            # Candidate corpus stays local/ignored; bounded report/selected/audit
            # materials are intentionally promoted for reproducible human review.
            if name in ("candidate", "task"):
                path = original.resolve()
                portable = False
            else:
                path = directory / ("report.md" if name == "report" else name + ".json")
                shutil.copyfile(original, path)
                if name in ("execution", "trace"):
                    # Curated JSON uses repository LF. Keep original runtime bytes
                    # untouched and reference/hash both representations explicitly.
                    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
                portable = True
            refs[name] = {"path": str(path.relative_to(ROOT)),
                          "sha256": sha256(path.read_bytes()), "tracked_portable": portable,
                          "original_runtime_path": str(original.relative_to(ROOT)),
                          "original_runtime_sha256": sha256(original.read_bytes()),
                          "serialization_note": "LF-normalized JSON copy; original bytes retained" if name in ("execution", "trace") else "original bytes"}
        report = (directory / "report.md").read_text(encoding="utf-8") if run["report"] else ""
        selected = read(source / cid / "selected.json")["evidences"]
        evidence = {e["evidence_id"]: e for e in selected}
        execution = result.get("execution") or {}
        ctx = execution.get("evidence_context") or {}
        assert selected == ctx.get("evidences", [])
        candidate = read(source / cid / "candidate.json")
        assert candidate["case_id"] == cid and candidate["task_id"] == task["task_id"]
        for evidence_item in selected:
            assert any(event["sub_query"] == evidence_item["sub_query"] and
                       record.get("source", record.get("url")) == evidence_item["url"] and
                       record["content"] == evidence_item["content"]
                       for event in candidate["events"] if event["stage"] == "eligible_chunks_before_ranking"
                       for record in event["records"]), evidence_item["evidence_id"]
        if run["status"] == "completed":
            assert refs["report"]["sha256"] == execution["report_sha256"]
            assert read(directory / "execution.json")["run_id"] == task["task_id"]
            assert read(directory / "trace.json")["trace_id"] == run["trace_id"]
        mapping = [{"claim_id": r["claim_id"], "rendered_text": r["rendered_text"],
                    "cited_evidence_ids": r["cited_evidence_ids"], "output_mode": r["output_mode"]}
                   for r in ctx.get("generated_claim_records", [])]
        write(directory / "citation_mapping.json", mapping)
        sheet = {"case_id": cid, "category": case["category"], "rubric_version": RUBRIC,
                 "status": "READY_FOR_HUMAN_REVIEW", "ai_preannotation_status": "COMPLETED",
                 "human_review_status": "PENDING", "reviewer": None}
        seen_units = set()
        claim_reviews = {i["review_id"]: i for i in recommendations[cid].get("claim_segmentation", [])}
        for section in SECTIONS:
            items = recommendations[cid].get(section, [])
            sheet[section + "_review"] = items
            for index, item in enumerate(items, 1):
                item.update(case_id=cid, category=case["category"], item_type=section,
                    review_id=item.get("review_id", f"{cid}-{section}-{index:03d}"),
                    annotation_kind="AI_ASSISTED_RECOMMENDATION", rubric_version=RUBRIC,
                    human_review_status="PENDING", reviewer_identity=None, human_decision=None,
                    review_timestamp=None, review_date=None, adjudication_note=None)
                assert item.get("ai_recommendation") is not None and item.get("reasoning")
                assert "ambiguity_flag" in item
                text = item.get("exact_report_text")
                if text:
                    assert text in report, (cid, text)
                    parent = item.get("exact_parent_report_text")
                    if not parent and item.get("claim_review_id"):
                        parent = claim_reviews[item["claim_review_id"]]["exact_parent_report_text"]
                        item["exact_parent_report_text"] = parent
                    if parent:
                        start = report.index(parent)
                        # A short type name such as vector must not match pgvector.
                        match = re.search(r"(?<![A-Za-z0-9_])" + re.escape(text) + r"(?![A-Za-z0-9_])", parent)
                        offset = match.start() if match else parent.index(text)
                        start += offset
                    else:
                        start = report.index(text)
                    item["report_span"] = [start, start + len(text)]
                    item["report_span_unit"] = "Unicode character offset in UTF-8 decoded report"
                    assert report[start:start+len(text)] == text
                item["saved_evidence"] = [{"evidence_id": eid, "source_reference": evidence[eid]["url"],
                    "exact_saved_evidence_excerpt": evidence[eid]["content"],
                    "excerpt_location": refs["selected"]["path"] + f"#/evidences/{selected.index(evidence[eid])}/content"}
                    for eid in item.get("evidence_ids", [])]
                if section == "required_unit":
                    unit = next(u for u in case["required_units"] if u["id"] == item["required_unit_id"])
                    item["exact_required_unit_text"] = unit["description"]
                    item["frozen_required_unit"] = unit
                    seen_units.add(unit["id"])
                if section == "claim_segmentation":
                    risks.update(item.get("risk_types", []))
                if section == "high_risk":
                    item["applicable_minimum_rules"] = sorted({rules["claim_gate_rules"]["risk_to_minimum_rule"][risk]
                        for risk in item["observed_risk_types"]})
                    item["combination_rule"] = "union_without_weakening"
                if section == "freshness":
                    policy = rules["evidence_policies"][case["category"]]
                    item["freshness_mode"] = policy["freshness_mode"]
                    item["max_age_days"] = policy["max_age_days"]
                    if item.get("publication_date"):
                        from datetime import date
                        item["age_at_cutoff_days"] = (date(2026, 9, 5)-date.fromisoformat(item["publication_date"])).days
                        item["within_age_window"] = 0 <= item["age_at_cutoff_days"] <= policy["max_age_days"]
                    else:
                        item["age_at_cutoff_days"] = None
                        item["within_age_window"] = None
                queue.append(item)
                counts[section] += 1
        assert seen_units == {u["id"] for u in case["required_units"]}
        write(directory / "review_sheet.json", sheet)
        write(directory / "artifact_references.json", {"case_id": cid, "run": run, "artifacts": refs,
            "portability": "candidate/task artifacts are ignored local files; selected excerpts and execution are tracked"})
        write(directory / "scoring_input.json", {"case_id": cid, "required_units": case["required_units"],
            "runtime_scoring": refs["scoring"], "annotations": "review_sheet.json",
            "status": "AI recommendations only, not evaluator-ready human gold"})
        hashes = {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in directory.iterdir()
                  if p.is_file() and p.name != "hashes.json"}
        hashes[refs["candidate"]["path"]] = refs["candidate"]["sha256"]
        hashes[refs["task"]["path"]] = refs["task"]["sha256"]
        write(directory / "hashes.json", hashes)
        entries.append({**run, "artifacts": refs, "ai_preannotation_status": "COMPLETED",
                        "provider_configuration": configuration,
                        "elapsed_s": diagnostic.get("elapsed_s"), "search_calls": diagnostic.get("search_calls"),
                        "search_count_scope": diagnostic.get("search_count_scope"),
                        "token_usage": None, "token_usage_availability": "not persisted by existing runtime",
                        "candidate_page_records": sum(len(e["records"]) for e in candidate["events"] if e["stage"] == "pages_before_compression"),
                        "eligible_chunk_records": sum(len(e["records"]) for e in candidate["events"] if e["stage"] == "eligible_chunks_before_ranking"),
                        "selected_evidence_count": len(selected), "emitted_record_count": len(mapping),
                        "human_review_status": "PENDING", "reviewer": None,
                        "review_sheet": str((directory / "review_sheet.json").relative_to(ROOT))})
    ambiguous = sum(item["ambiguity_flag"] for item in queue)
    write(PACKAGE / "HUMAN_REVIEW_QUEUE.json", {"human_review_status": "PENDING", "reviewer": None, "items": queue})
    lines = ["# Six-case populated human review queue", "", "AI recommendations only. Every human decision remains pending.",
             "Markdown trims line-end whitespace for display. Exact excerpt characters are preserved in HUMAN_REVIEW_QUEUE.json and selected.json.", ""]
    for item in queue:
        lines += [f"## {item['review_id']}", "", f"Case/category: {item['case_id']} / {item['category']}", "",
                  f"Type: {item['item_type']}; flags: {', '.join(item.get('flags', []))}", "",
                  "Exact report/unit text:", "", item.get("exact_report_text") or item.get("exact_required_unit_text") or item.get("source_identity_information", "Source review"), "",
                  f"AI_ASSISTED_RECOMMENDATION: {item['ai_recommendation']}", "", item["reasoning"], "",
                  "Uncertainty: " + item.get("uncertainty_reason", "Requires human confirmation"), ""]
        if item.get("exact_required_unit_text"):
            lines += ["Frozen Required Unit: " + item["exact_required_unit_text"], ""]
        if item.get("exact_parent_report_text"):
            lines += ["Parent report sentence: " + item["exact_parent_report_text"], ""]
        if item.get("exact_date_evidence_excerpt"):
            lines += ["Saved date evidence: " + item["exact_date_evidence_excerpt"],
                      "Location: " + item["date_evidence_location"], ""]
        for evidence_item in item["saved_evidence"]:
            lines += [f"Evidence: {evidence_item['evidence_id']} — {evidence_item['source_reference']}", "",
                      "```text", evidence_item["exact_saved_evidence_excerpt"], "```", ""]
        lines += ["reviewer_identity: null; human_decision: null; review_timestamp: null; adjudication_note: null", ""]
    rendered = "\n".join(line.rstrip() for line in "\n".join(lines).splitlines()) + "\n"
    (PACKAGE / "HUMAN_REVIEW_QUEUE.md").write_bytes(rendered.encode("utf-8"))
    estimates = [r["cost_usd_runtime_estimate"] for r in runs]
    manifest = {"benchmark_schema": RUBRIC, "dataset_sha256": DATASET_SHA, "cutoff": "2026-09-05",
        "rubric_version": RUBRIC, "rubric_reference": "docs/v2/V2_BENCHMARK_SPEC.md",
        "package_status": "READY_FOR_HUMAN_REVIEW", "selected_development_case_ids": list(IDS),
        "execution_code_commit": "fa385086", "cases": entries,
        "ai_preannotation_status": "COMPLETED", "human_review_status": "PENDING", "reviewer": None,
        "counts": dict(counts), "human_review_item_count": len(queue), "unresolved_count": ambiguous,
        "atomic_factual_claim_count": sum(i["item_type"] == "claim_segmentation" and i.get("factual_or_nonfactual") == "factual" for i in queue),
        "nonfactual_segment_count": sum(i["item_type"] == "claim_segmentation" and i.get("factual_or_nonfactual") == "non-factual" for i in queue),
        "confident_recommendations_requiring_confirmation": len(queue)-ambiguous,
        "actual_emitted_claim_risk_type_coverage": sorted(risks),
        "uncovered_risk_types": sorted(set(rules["claim_gate_rules"]["risk_to_minimum_rule"])-risks),
        "calibration_provider_cost_usd": None,
        "runtime_estimated_cost_usd": sum(estimates) if all(v is not None for v in estimates) else None,
        "cost_note": "Runtime estimate is not provider billing; generic pricing/local embedding estimate may be inaccurate; search billing unavailable.",
        "official_benchmark_cost_usd": 0, "official_holdout_executions": 0,
        "portability": "Tracked review excerpts are portable; candidate and task references require the original ignored local outputs."}
    write(PACKAGE / "CALIBRATION_MANIFEST.json", manifest)
    verified = 0
    for run in runs:
        path = PACKAGE / run["category"] / run["case_id"] / "hashes.json"
        for name, expected in read(path).items():
            target = Path(name)
            if not target.is_absolute():
                target = ROOT / target
            assert sha256(target.read_bytes()) == expected, name
            verified += 1
    assert sha256((ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json").read_bytes()) == DATASET_SHA
    write(PACKAGE / "VALIDATION.json", {"status": "PASSED", "verified_artifact_hashes": verified,
        "dataset_sha256_verified": DATASET_SHA, "case_run_report_evidence_mapping_review_trace_links": "verified",
        "human_fields_unset": True, "required_units": counts["required_unit"], "official_holdout_executions": 0})
    print(json.dumps({"counts": dict(counts), "items": len(queue), "ambiguous": ambiguous, "verified_hashes": verified}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--recommendations", type=Path, required=True)
    args = parser.parse_args()
    package(args.source.resolve(), read(args.recommendations))
