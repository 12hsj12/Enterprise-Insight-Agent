"""Legacy execution must preserve unknown structured evaluation metrics."""

from benchmarks.evaluation import ExecutionStatus
from gpt_researcher.enterprise.workflow import IntelligenceRequest, IntelligenceResult
from gpt_researcher.evidence.models import EvidenceConsistencyAssessment


def test_legacy_result_can_expose_artifacts_without_structured_metrics():
    result = IntelligenceResult(
        run_id="legacy-run",
        request=IntelligenceRequest(target="Acme"),
        report="Legacy report",
        evidences=[],
        assessments=[],
        consistency=EvidenceConsistencyAssessment(status="insufficient"),
        source_urls=[],
        output_artifact_reference="outputs/enterprise/legacy-run.md",
        trace_id="legacy-trace",
        trace_artifact_reference="outputs/enterprise/traces/legacy-trace.json",
        estimated_cost_usd=0.125,
    )

    case = result.to_evaluation_case("legacy-smoke")

    assert case.execution_status is ExecutionStatus.COMPLETED
    assert case.case_id == "legacy-smoke"
    assert case.artifact_reference == result.output_artifact_reference
    assert case.trace_id == result.trace_id
    assert case.trace_artifact_reference == result.trace_artifact_reference
    assert case.efficiency.estimated_cost_usd == 0.125
    assert case.evidence is None
    assert case.claim_gate is None
    assert case.grounding is None
