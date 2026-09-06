import pytest
from pydantic import ValidationError

from gpt_researcher.enterprise import IntelligenceRequest, IntelligenceResult, IntelligenceWorkflow
from gpt_researcher.evidence import Evidence
from gpt_researcher.evidence.reliability import EvidenceReliabilityEvaluator


class FakeResearcher:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.researched = False
        self.evidence = Evidence(evidence_id="ev_test", sub_query=kwargs["query"],
            title="Fixture", url="https://example.com/product", content="FixtureCo sells a widget.")

    async def conduct_research(self):
        self.researched = True

    async def write_report(self, custom_prompt):
        assert self.researched
        assert "2026-09-05" in custom_prompt
        return "FixtureCo sells a [widget](https://example.com/product). Risks remain unknown."

    def get_evidences(self):
        return [self.evidence, self.evidence]

    def get_evidence_assessments(self):
        return [EvidenceReliabilityEvaluator().evaluate(self.evidence)]

    def get_costs(self):
        return 0.0


async def test_local_end_to_end_and_serialization():
    result = await IntelligenceWorkflow(FakeResearcher).run(IntelligenceRequest(target="FixtureCo"), "run-test")
    assert result.run_id == "run-test"
    assert len(result.evidences) == 1
    assert result.source_urls == ["https://example.com/product"]
    assert result.consistency.status == "insufficient"
    assert IntelligenceResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("target", ["", "   ", "x" * 301])
def test_rejects_invalid_target(target):
    with pytest.raises(ValidationError):
        IntelligenceRequest(target=target)


def test_query_is_generic_and_cutoff_explicit():
    request = IntelligenceRequest(target="Another company", topic="Developer tools")
    assert "Another company" in request.research_query()
    assert "Developer tools" in request.research_query()
    assert "2026-09-05" in request.research_query()


async def test_broken_assessment_invariant_fails():
    class Broken(FakeResearcher):
        def get_evidence_assessments(self):
            return []
    with pytest.raises(ValueError, match="IDs must match"):
        await IntelligenceWorkflow(Broken).run(IntelligenceRequest(target="FixtureCo"))


async def test_provider_failure_is_not_a_success():
    class Broken(FakeResearcher):
        async def conduct_research(self):
            raise ConnectionError("fixture failure")
    with pytest.raises(ConnectionError):
        await IntelligenceWorkflow(Broken).run(IntelligenceRequest(target="FixtureCo"))


async def test_empty_report_is_not_a_success():
    class Empty(FakeResearcher):
        async def write_report(self, **kwargs):
            return "   "
    with pytest.raises(ValueError, match="empty report"):
        await IntelligenceWorkflow(Empty).run(IntelligenceRequest(target="FixtureCo"))
