import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from benchmarks.evaluation import EvaluationAdapter, ExecutionStatus
from gpt_researcher.enterprise.trace import (
    EvidenceSelectionEvent,
    ResearchExecutionStatus,
    ResearchTrace,
    ResearchTraceRecorder,
)
from gpt_researcher.evidence import (
    Claim,
    ClaimEvidenceLink,
    ClaimGate,
    ClaimRiskType,
    Evidence,
    EvidenceContext,
    GeneratedClaimRecord,
    GroundingFinding,
    GroundingFindingCode,
    GroundingRepairAction,
    GroundingRepairOperation,
    GroundingRepairPlan,
    GroundingStatus,
    GroundingValidationResult,
    GroundingValidator,
)
from gpt_researcher.evidence.models import RetrievalDiagnostic


class DeterministicTime:
    def __init__(self):
        self._base = datetime(2026, 9, 10, tzinfo=timezone.utc)
        self._clock_calls = 0
        self._timer_value = 100.0

    def clock(self):
        value = self._base + timedelta(seconds=self._clock_calls)
        self._clock_calls += 1
        return value

    def timer(self):
        value = self._timer_value
        self._timer_value += 1.0
        return value


def recorder(**kwargs):
    deterministic = DeterministicTime()
    return ResearchTraceRecorder(
        run_id="run-7",
        trace_id="trace-7",
        case_id="EI_V2_001",
        query_reference="benchmark:EI_V2_001",
        clock=deterministic.clock,
        timer=deterministic.timer,
        **kwargs,
    )


def evidence_context():
    evidence = Evidence(
        evidence_id="ev-1",
        sub_query="private query",
        content="private scraped content",
        url="https://example.com/?api_key=secret",
    )
    return EvidenceContext(
        context="private prompt context",
        evidences=[evidence],
        retrieval_diagnostics=[
            RetrievalDiagnostic(
                evidence_id=evidence.evidence_id,
                similarity_score=0.8,
                authority_score=0.6,
                final_score=0.76,
            )
        ],
    )


def claim_and_gate():
    claim = Claim(
        scope_id="EI_V2_001",
        normalized_text="Revenue was 10 million.",
        risk_types=(ClaimRiskType.NUMERIC_VALUE,),
        is_material=True,
    )
    return claim, ClaimGate().evaluate(claim, [], [])


def grounding_artifacts(claim):
    record = GeneratedClaimRecord(
        claim_id=claim.claim_id,
        rendered_text="private full generated text",
        cited_evidence_ids=("ev-unknown",),
    )
    result = GroundingValidationResult(
        status=GroundingStatus.REPAIR_REQUIRED,
        findings=(
            GroundingFinding(
                code=GroundingFindingCode.UNKNOWN_CITATION,
                claim_id=claim.claim_id,
                evidence_id="ev-unknown",
            ),
        ),
        repairable_claim_ids=(claim.claim_id,),
        reason_codes=(GroundingFindingCode.UNKNOWN_CITATION,),
        repair_attempt=0,
    )
    plan = GroundingRepairPlan(
        actions=(
            GroundingRepairAction(
                operation=GroundingRepairOperation.REMOVE_INVALID_CITATION,
                claim_id=claim.claim_id,
                evidence_id="ev-unknown",
            ),
        )
    )
    return record, result, plan


def completed_trace():
    item = recorder()
    context = evidence_context()
    claim, gate = claim_and_gate()
    record, grounding, plan = grounding_artifacts(claim)
    item.record_evidence_selection(
        context,
        authority_weight=0.2,
        similarity_threshold=0.42,
        task_category="factual_verification",
        candidate_evidence_count=3,
    )
    item.record_claim_gate(claim, gate)
    item.record_generation([record], output_artifact_reference="reports/EI_V2_001.md")
    item.record_grounding_validation(grounding, [record], repair_plan=plan)
    item.record_repair(plan)
    return item.complete(
        final_claim_count=1,
        output_artifact_reference="reports/EI_V2_001.md",
    )


def test_basic_trace_lifecycle_and_typed_event_append():
    trace = completed_trace()
    assert trace.execution_status is ResearchExecutionStatus.COMPLETED
    assert trace.started_at < trace.completed_at
    assert [event.sequence for event in trace.events] == list(range(len(trace.events)))
    assert [event.event_type.value for event in trace.events] == [
        "research_started",
        "evidence_selection",
        "claim_gate",
        "generation",
        "grounding_validation",
        "repair",
        "research_completed",
    ]


def test_recorder_accepts_a_typed_event_with_explicit_sequence():
    item = recorder()
    event = EvidenceSelectionEvent(
        sequence=1,
        recorded_at=datetime(2026, 9, 10, 0, 0, 1, tzinfo=timezone.utc),
        selected_evidence_count=0,
    )
    item.append(event)
    assert item.events[1] is event
    with pytest.raises(ValueError, match="append order"):
        item.append(event.model_copy(update={"sequence": 3}))


def test_evidence_selection_serialization_is_bounded_and_payload_free():
    payload = completed_trace().to_json()
    parsed = json.loads(payload)
    event = parsed["events"][1]
    assert event["candidate_evidence_count"] == 3
    assert event["selected_evidence_count"] == 1
    assert event["selected_evidence_ids"] == ["ev-1"]
    assert event["scorer_summary"][0]["final_score"] == 0.76
    assert "private scraped content" not in payload
    assert "private prompt context" not in payload
    assert "api_key" not in payload


def test_unsafe_ids_and_references_are_deterministically_redacted():
    item = recorder()
    context = EvidenceContext(
        context="private",
        evidences=[
            Evidence(
                evidence_id="https://example.test/?api_key=SECRET_VALUE",
                sub_query="private",
                content="private",
            )
        ],
    )
    item.record_evidence_selection(
        context, authority_weight=0.2, similarity_threshold=0.4
    )
    item.retrieval(context, 0.2, 0.4)
    trace = item.complete(
        output_artifact_reference="https://signed.test/report?token=SECRET_VALUE"
    )
    payload = trace.to_json()
    assert "SECRET_VALUE" not in payload
    assert "https://" not in payload
    assert "redacted_" in payload
    assert "SECRET_VALUE" not in json.dumps(item.snapshot())


def test_claim_gate_grounding_repair_and_completion_serialization():
    parsed = json.loads(completed_trace().to_json())
    gate = parsed["events"][2]
    assert gate["risk_types"] == ["numeric_value"]
    assert gate["is_material"] is True
    assert gate["evidence_strength_rules"] == ["primary_or_two_independent"]
    assert gate["gate_decision"] == "omit"
    grounding = parsed["events"][4]
    assert grounding["finding_codes"] == ["unknown_citation"]
    assert grounding["cited_evidence_count"] == 1
    assert grounding["repair_required"] is True
    assert grounding["planned_repair_action_types"] == [
        "remove_invalid_citation"
    ]
    repair = parsed["events"][5]
    assert repair["action_type"] == "remove_invalid_citation"
    assert parsed["events"][-1]["final_claim_count"] == 1


def test_trace_json_roundtrip_and_stable_serialization_for_recorded_sequence():
    first = completed_trace()
    second = completed_trace()
    assert first.to_json().encode("utf-8") == second.to_json().encode("utf-8")
    assert ResearchTrace.model_validate_json(first.to_json()) == first


def test_failure_is_bounded_and_optional_metadata_remains_null():
    item = recorder()
    trace = item.fail(ConnectionError("Authorization: Bearer secret-token"))
    payload = json.loads(trace.to_json())
    assert payload["execution_status"] == "failed"
    assert payload["error"] == {"error_code": None, "error_type": "ConnectionError"}
    assert payload["run_id"] == "run-7"
    assert payload["completed_at"] is not None
    assert payload["output_artifact_reference"] is None
    assert "secret-token" not in trace.to_json()

    empty_metadata = ResearchTraceRecorder(trace_id="trace-no-metadata").complete()
    empty_payload = json.loads(empty_metadata.to_json())
    assert empty_payload["run_id"] is None
    assert empty_payload["case_id"] is None
    assert empty_payload["query_reference"] is None


def test_non_finite_numbers_and_unknown_event_fail_deterministically():
    with pytest.raises(ValidationError):
        EvidenceSelectionEvent(
            sequence=1,
            recorded_at=datetime.now(timezone.utc),
            selected_evidence_count=0,
            authority_weight=float("nan"),
        )
    payload = json.loads(completed_trace().to_json())
    payload["events"][1]["event_type"] = "unknown"
    with pytest.raises(ValidationError, match="union_tag_invalid"):
        ResearchTrace.model_validate(payload)
    serialized = completed_trace().to_json()
    assert "NaN" not in serialized and "Infinity" not in serialized


def test_local_export_uses_trace_id_and_refuses_overwrite(tmp_path):
    trace = completed_trace()
    # Recreate a recorder because completed_trace returns the immutable model.
    item = recorder()
    item.complete()
    path = item.export(tmp_path / "outputs" / "traces")
    assert path.name == "trace-7.json"
    assert ResearchTrace.model_validate_json(path.read_text(encoding="utf-8")) == item.trace()
    with pytest.raises(FileExistsError):
        item.export(tmp_path / "outputs" / "traces")
    assert trace.schema_version == "enterprise-research-trace/1.0.0"


def test_evaluation_case_result_associates_trace_without_parsing_it():
    case = EvaluationAdapter.from_structured_result(
        case_id="EI_V2_001",
        execution_status=ExecutionStatus.COMPLETED,
        trace_id="trace-7",
        trace_artifact_reference="outputs/traces/trace-7.json",
    )
    assert case.trace_id == "trace-7"
    assert case.trace_artifact_reference == "outputs/traces/trace-7.json"
    assert case.evidence is None and case.claim_gate is None and case.grounding is None


def test_export_failure_does_not_mutate_gate_or_grounding_results(tmp_path):
    claim, gate = claim_and_gate()
    record, grounding, plan = grounding_artifacts(claim)
    gate_before = gate.model_dump()
    grounding_before = grounding.model_dump()
    item = recorder()
    item.record_claim_gate(claim, gate)
    item.record_grounding_validation(grounding, [record], repair_plan=plan)
    item.complete()
    not_a_directory = tmp_path / "occupied"
    not_a_directory.write_text("fixture", encoding="utf-8")
    assert item.try_export(not_a_directory) is None
    assert item.last_export_error_type == "FileExistsError"
    assert gate.model_dump() == gate_before
    assert grounding.model_dump() == grounding_before


def test_active_trace_observes_actual_gate_grounding_and_applied_repair():
    item = recorder()
    claim = Claim(scope_id="case", normalized_text="Unsupported fact")
    record = GeneratedClaimRecord(
        claim_id=claim.claim_id,
        rendered_text="Unsupported fact",
    )
    with item.activate():
        gate = ClaimGate().evaluate(claim, [], [])
        validation = GroundingValidator().validate(
            [record],
            claims=[claim],
            evidences=[],
            links=[
                ClaimEvidenceLink(
                    claim_id=claim.claim_id,
                    evidence_id="unknown",
                    relation="support",
                )
            ],
            gate_results=[gate],
        )
        plan = GroundingValidator.create_repair_plan(validation)
        GroundingValidator.apply_repair_plan([record], plan)
    item.complete()
    event_types = [event.event_type.value for event in item.events]
    assert "claim_gate" in event_types
    assert "grounding_validation" in event_types
    assert "repair" in event_types
    gate_phases = [
        event.phase.value
        for event in item.events
        if event.event_type.value == "claim_gate"
    ]
    assert gate_phases == ["pre_generation", "grounding_revalidation"]
