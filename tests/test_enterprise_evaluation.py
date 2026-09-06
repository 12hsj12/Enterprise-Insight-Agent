import json

import pytest
from pydantic import ValidationError

from benchmarks.metrics import QualityAnnotation, quality_metrics, summarize
from benchmarks.run import digest, load_cases, run_benchmark
from benchmarks.score import score_run


def annotation(**overrides):
    values = dict(run_id="run", report_sha256=digest("report"), reviewer="fixture reviewer",
        method="human counts; synthetic test only", required_facts=4, supported_required_facts=3,
        evaluated_citations=5, supporting_citations=4, factual_claims=10,
        claims_with_evidence=6, unsupported_claims=4)
    return QualityAnnotation(**(values | overrides))


def test_quality_formulas():
    assert quality_metrics(annotation()) == dict(evidence_coverage=0.75, citation_correctness=0.8,
        citation_completeness=0.6, unsupported_claim_rate=0.4)
    assert all(v is None for v in quality_metrics(None).values())


def test_undefined_denominators_and_bad_counts():
    a = annotation(evaluated_citations=0, supporting_citations=0, factual_claims=0,
                   claims_with_evidence=0, unsupported_claims=0)
    assert quality_metrics(a)["citation_correctness"] is None
    with pytest.raises(ValidationError):
        annotation(supporting_citations=6)
    with pytest.raises(ValidationError):
        annotation(unsupported_claims=1)


def test_frozen_split_and_failure_denominator():
    assert len(load_cases("development")[1]) == 8
    assert len(load_cases("holdout")[1]) == 4
    assert summarize([{"status": "failed", "latency_s": 2}, {"status": "completed", "latency_s": 4}])["failure_rate"] == 0.5


async def test_dry_run_schema_and_no_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_RELIABILITY_WEIGHT", raising=False)
    def forbidden(**kwargs):
        raise AssertionError("dry run cannot construct provider")
    output = tmp_path / "dry"
    summary = await run_benchmark("baseline", "development", output, researcher_factory=forbidden)
    assert summary["attempted"] == 0
    assert summary["cases"] == 8
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest["commit_sha"]) == 40
    assert manifest["config"]["SOURCE_RELIABILITY_WEIGHT"] == 0
    records = json.loads((output / "results.json").read_text())
    assert all(r["citation_correctness"] is None for r in records)
    with pytest.raises(FileExistsError):
        await run_benchmark("baseline", "development", output)


async def test_failed_live_fixture_kept_without_sensitive_error(tmp_path):
    def broken(**kwargs):
        raise ConnectionError("secret-token-do-not-record")
    output = tmp_path / "failed"
    summary = await run_benchmark("baseline", "development", output, True, broken)
    assert summary["failure_rate"] == 1
    assert summary["failures"] == 8
    assert "secret-token" not in (output / "results.json").read_text()


async def test_completed_fixture_and_annotation_hash(tmp_path):
    class Researcher:
        def __init__(self, **kwargs): pass
        async def conduct_research(self): return ["fixture context"]
        async def write_report(self): return "report"
        def get_evidences(self): return []
        def get_research_sources(self): return [{"url": "https://example.com"}]
        def get_costs(self): return 0.0
    output = tmp_path / "raw"
    await run_benchmark("baseline", "development", output, True, Researcher)
    records = json.loads((output / "results.json").read_text())
    a = annotation(run_id=records[0]["run_id"])
    path = tmp_path / "annotations.json"
    path.write_text(json.dumps([a.model_dump()]))
    score_run(output, path, tmp_path / "scored")
    assert json.loads((tmp_path / "scored/summary.json").read_text())["quality_reviewed_cases"] == 1
    assert json.loads((output / "results.json").read_text())[0]["quality_annotation"] is None
    path.write_text(json.dumps([annotation(run_id=a.run_id, report_sha256="a" * 64).model_dump()]))
    with pytest.raises(ValueError, match="hash mismatch"):
        score_run(output, path, tmp_path / "bad")
