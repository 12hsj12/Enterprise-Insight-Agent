import copy
import json
from types import SimpleNamespace

from gpt_researcher.enterprise.calibration_capture import CalibrationCapture, canonical_bytes, observe, sha256
from gpt_researcher.enterprise.calibration_capture import scrub


def test_observation_detached_distinct_stable_and_scoped(monkeypatch):
    monkeypatch.setenv("SAMPLE_API_KEY", "test-private-secret")
    pages = [{"url": "https://example.org", "raw_content": "saved text", "Authorization": "test-private-secret"}]
    doc = SimpleNamespace(metadata={"source": "https://example.org"}, page_content="saved",
                          state={"query_similarity_score": 0.75})
    before = copy.deepcopy((pages, doc.__dict__))
    outputs = []
    for _ in range(2):
        capture = CalibrationCapture()
        with capture.activate():
            observe("pages_before_compression", "query", pages)
            observe("eligible_chunks_before_ranking", "query", [doc])
        observe("pages_before_compression", "outside", pages)
        outputs.append(canonical_bytes(capture.events))
        assert len(capture.events) == 2 and not capture.errors
    assert (pages, doc.__dict__) == before
    assert outputs[0] == outputs[1] and sha256(outputs[0]) == sha256(outputs[1])
    assert b"test-private-secret" not in outputs[0] and b"Authorization" not in outputs[0]
    data = json.loads(outputs[0])
    assert data[0]["records"][0]["content"] != data[1]["records"][0]["content"]


def test_malformed_and_nonfinite_fail_without_mutation():
    capture = CalibrationCapture()
    doc = SimpleNamespace(metadata={}, page_content="text", state={"query_similarity_score": float("nan")})
    with capture.activate():
        observe("pages_before_compression", "query", [object()])
        observe("eligible_chunks_before_ranking", "query", [doc])
    assert capture.events == []
    assert capture.errors == ["capture_invalid_material"] * 2


def test_bounded_text_redacted(monkeypatch):
    monkeypatch.setenv("TEST_TOKEN", "secret-in-page")
    capture = CalibrationCapture()
    with capture.activate():
        observe("pages_before_compression", "q", [{"raw_content": "secret-in-page" + "x" * 60000}])
    record = capture.events[0]["records"][0]
    assert record["content_truncated"] and len(record["content"]) == 50000
    assert "secret-in-page" not in record["content"]


def test_auth_and_url_redaction():
    for value in ("Authorization: Bearer private-value", "Authorization: Basic private-value",
                  "https://user:private-value@example.org", "https://example.org?token=private-value"):
        assert "private-value" not in scrub(value)


def test_nontext_optional_metadata_keeps_candidate():
    capture = CalibrationCapture()
    with capture.activate():
        observe("pages_before_compression", "q", [{"raw_content": "text", "author": ["name"]}])
    assert not capture.errors
    assert capture.events[0]["records"][0]["content"] == "text"
    assert capture.events[0]["records"][0]["ignored_nontext_metadata_fields"] == ["author"]


async def test_capture_preserves_actual_ranking_gate_grounding(monkeypatch):
    from datetime import date
    from langchain_core.documents import Document
    from langchain_community.document_transformers.embeddings_redundant_filter import get_stateful_documents
    from gpt_researcher.context.compression import ContextCompressor
    from gpt_researcher.enterprise.integration import ClaimPlan, RegisteredClaimInput, integrate_claims, render_report
    from gpt_researcher.evidence.models import Claim, ClaimEvidenceLink
    docs = get_stateful_documents([Document(page_content="Acme builds widgets.", metadata={"source": "https://example.org"}),
                                  Document(page_content="Other text.", metadata={"source": "https://example.net"})])
    for doc, score in zip(docs, (0.8, 0.6)):
        doc.state["query_similarity_score"] = score
    calls = []
    class Retriever:
        def invoke(self, query, **kwargs):
            calls.append(query)
            return docs
    compressor = ContextCompressor(documents=[{"raw_content": "Acme builds widgets. Other text."}],
                                   embeddings=None, source_reliability_weight=0.2)
    monkeypatch.setattr(compressor, "_ContextCompressor__get_contextual_retriever", lambda: Retriever())
    async def run():
        context = await compressor.async_get_context("q", max_results=1)
        claim = Claim(scope_id="fixture", normalized_text="Acme builds widgets.")
        eid = context.evidences[0].evidence_id
        execution = integrate_claims(context, ClaimPlan(items=[RegisteredClaimInput(claim=claim,
            links=[ClaimEvidenceLink(claim_id=claim.claim_id, evidence_id=eid, relation="support")],
            cited_evidence_ids=[eid])]), date(2026, 9, 5))
        return render_report(execution), execution.model_dump(mode="json")
    without = await run()
    capture = CalibrationCapture()
    with capture.activate():
        captured = await run()
    assert without == captured
    assert calls == ["q", "q"]
    assert len(capture.events[1]["records"]) == 2
    assert len(captured[1]["evidence_context"]["evidences"]) == 1
