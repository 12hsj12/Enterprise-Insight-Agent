import asyncio
import json
from types import SimpleNamespace

import pytest

from gpt_researcher.enterprise.trace import RunTrace, current_trace
from gpt_researcher.evidence import Evidence, EvidenceContext
from gpt_researcher.evidence.models import RetrievalDiagnostic
from gpt_researcher.skills.researcher import ResearchConductor


async def test_concurrent_run_isolation_and_reset():
    async def one(name):
        trace = RunTrace(name)
        with trace.activate():
            await asyncio.sleep(0)
            assert current_trace() is trace
        return trace.snapshot()
    snapshots = await asyncio.gather(one("one"), one("two"))
    assert [s["run_id"] for s in snapshots] == ["one", "two"]
    assert current_trace() is None


def test_error_redaction_and_bounded_events():
    trace = RunTrace("test", max_events=1)
    with pytest.raises(ConnectionError):
        with trace.stage("research"):
            raise ConnectionError("secret-token")
    with trace.stage("report"):
        pass
    summary = trace.snapshot()
    assert summary["dropped_events"] == 1
    assert summary["events"][0]["error_type"] == "ConnectionError"
    assert "secret-token" not in json.dumps(summary)


def test_selection_has_scores_without_content_or_urls():
    trace = RunTrace("test")
    result = EvidenceContext(context="private", evidences=[Evidence(
        evidence_id="ev", sub_query="private", content="private", url="https://example.com?secret=key")],
        retrieval_diagnostics=[RetrievalDiagnostic(evidence_id="ev", similarity_score=0.8,
            authority_score=0.6, final_score=0.76)])
    trace.retrieval(result, 0.2, 0.42)
    summary = trace.snapshot()
    assert summary["selected_evidence_count"] == 1
    assert summary["events"][0]["scores"][0]["final_score"] == 0.76
    assert "private" not in json.dumps(summary)
    assert "secret" not in json.dumps(summary)


async def test_actual_search_boundary_counts_attempts_and_errors():
    class BrokenSearch:
        def __init__(self, *a, **kw): pass
        def search(self, **kw): raise ConnectionError("fixture")
    researcher = SimpleNamespace(retrievers=[BrokenSearch], cfg=SimpleNamespace(max_search_results_per_query=5),
                                 visited_urls=set(), verbose=False)
    trace = RunTrace("search")
    with trace.activate():
        await ResearchConductor(researcher)._search_relevant_source_urls("query")
    assert trace.search_calls == 1
    assert trace.search_failures == 1
    assert trace.events[0]["status"] == "failed"
