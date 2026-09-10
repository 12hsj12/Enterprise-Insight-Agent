import pytest
from pydantic import ValidationError

from gpt_researcher.enterprise import IntelligenceRequest, IntelligenceResult, IntelligenceWorkflow
from gpt_researcher.enterprise.trace import ResearchTrace, ResearchTraceRecorder
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


async def test_workflow_exports_completed_trace_without_report_payload(tmp_path):
    recorder = ResearchTraceRecorder(run_id="run-traced", trace_id="trace-workflow")
    result = await IntelligenceWorkflow(FakeResearcher).run(
        IntelligenceRequest(target="FixtureCo"),
        trace=recorder,
        trace_output_directory=tmp_path / "traces",
        output_artifact_reference="reports/run-traced.md",
    )
    path = tmp_path / "traces" / "trace-workflow.json"
    trace = ResearchTrace.model_validate_json(path.read_text(encoding="utf-8"))
    assert result.trace_id == "trace-workflow"
    assert result.trace_artifact_reference == str(path)
    assert trace.execution_status.value == "completed"
    assert trace.output_artifact_reference == "reports/run-traced.md"
    assert [event.event_type.value for event in trace.events] == [
        "research_started", "generation", "research_completed"
    ]
    assert "FixtureCo sells" not in path.read_text(encoding="utf-8")


async def test_workflow_exports_bounded_failure_trace_and_reraises(tmp_path):
    class Broken(FakeResearcher):
        async def conduct_research(self):
            raise ConnectionError("secret provider response")

    recorder = ResearchTraceRecorder(run_id="run-failed", trace_id="trace-failed")
    with pytest.raises(ConnectionError, match="secret provider response"):
        await IntelligenceWorkflow(Broken).run(
            IntelligenceRequest(target="FixtureCo"),
            trace=recorder,
            trace_output_directory=tmp_path / "traces",
        )
    payload = (tmp_path / "traces" / "trace-failed.json").read_text(
        encoding="utf-8"
    )
    trace = ResearchTrace.model_validate_json(payload)
    assert trace.execution_status.value == "failed"
    assert trace.error.error_type == "ConnectionError"
    assert "secret provider response" not in payload


async def test_observer_timer_failure_does_not_change_successful_research():
    calls = 0

    def timer():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("observer timer broke")
        return 1.0

    recorder = ResearchTraceRecorder(
        run_id="run-timer", trace_id="trace-timer", timer=timer
    )
    result = await IntelligenceWorkflow(FakeResearcher).run(
        IntelligenceRequest(target="FixtureCo"), trace=recorder
    )
    assert result.run_id == "run-timer"
    assert result.trace_id == "trace-timer"
    assert recorder.last_record_error_type == "RuntimeError"


async def test_terminal_observer_failure_does_not_export_running_trace(tmp_path):
    calls = 0

    def clock():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("observer clock broke")
        from datetime import datetime, timezone

        return datetime(2026, 9, 10, tzinfo=timezone.utc)

    recorder = ResearchTraceRecorder(
        run_id="run-clock", trace_id="trace-clock", clock=clock
    )
    result = await IntelligenceWorkflow(FakeResearcher).run(
        IntelligenceRequest(target="FixtureCo"),
        trace=recorder,
        trace_output_directory=tmp_path / "traces",
    )
    assert result.run_id == "run-clock"
    assert result.trace_artifact_reference is None
    assert not (tmp_path / "traces" / "trace-clock.json").exists()
