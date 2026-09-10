import json
from datetime import datetime, timezone

import pytest

from benchmarks.evaluation import (
    BenchmarkContractCaseMetrics,
    EfficiencyCaseMetrics,
    EvaluationAdapter,
    EvaluationCaseResult,
    EvaluationError,
    EvaluationRun,
    EvaluationRunMetadata,
    ExecutionStatus,
    V2_ARCHITECTURE_VERSION,
    V2_BENCHMARK_SCHEMA_VERSION,
    V2_DATASET_SHA256,
    compare_evaluation_runs,
    evaluate_run,
    load_frozen_v2_benchmark,
    metadata_for_frozen_v2,
    render_comparison_markdown,
    write_comparison_artifacts,
    write_run_artifacts,
)
from gpt_researcher.evidence import (
    Claim,
    ClaimEvidenceQualification,
    ClaimGateDecision,
    ClaimGateReasonCode,
    ClaimGateResult,
    Evidence,
    EvidenceContext,
    EvidenceStrengthRule,
    GeneratedClaimRecord,
    GroundingStatus,
    GroundingValidationResult,
    ResolvedClaimGateObligations,
)


SYNTHETIC_DATASET_SHA = "b" * 64


def metadata(label="enterprise-v2", dataset_sha=SYNTHETIC_DATASET_SHA):
    return EvaluationRunMetadata(
        run_id=f"run-{label}",
        run_label=label,
        architecture_version=V2_ARCHITECTURE_VERSION,
        benchmark_schema_version="evaluation-fixture/1.0.0",
        dataset_sha256=dataset_sha,
        source_commit=None,
        model_identifier=None,
        provider_identifier=None,
        benchmark_cutoff_date="2026-09-05",
        started_at=datetime(2026, 9, 10, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 9, 10, 1, 1, tzinfo=timezone.utc),
    )


def completed_case(case_id, latency, *, contract=True):
    return EvaluationCaseResult(
        case_id=case_id,
        execution_status="completed",
        benchmark_contract=BenchmarkContractCaseMetrics(
            passed=contract,
            required_units_satisfied=2 if contract else 1,
            required_units_total=2,
        ),
        efficiency=EfficiencyCaseMetrics(latency_seconds=latency),
    )


def gate_result(item, decision):
    rules = (EvidenceStrengthRule.STANDARD,)
    return ClaimGateResult(
        claim_id=item.claim_id,
        decision=decision,
        required_rules=rules,
        resolved_obligations=ResolvedClaimGateObligations(
            evidence_strength_rules=rules
        ),
        reason_codes=(
            ClaimGateReasonCode.ALL_REQUIREMENTS_SATISFIED
            if decision is ClaimGateDecision.EMIT
            else ClaimGateReasonCode.EVIDENCE_REQUIREMENTS_UNMET,
        ),
    )


def structured_context():
    claims = [
        Claim(scope_id="case", normalized_text="Material fact", is_material=True),
        Claim(scope_id="case", normalized_text="Minor fact", is_material=False),
        Claim(scope_id="case", normalized_text="Omitted fact", is_material=True),
        Claim(scope_id="case", normalized_text="Retrieve fact", is_material=True),
    ]
    decisions = list(ClaimGateDecision)
    return EvidenceContext(
        context="fixture",
        evidences=[
            Evidence(evidence_id="ev-b", sub_query="q", content="b"),
            Evidence(evidence_id="ev-a", sub_query="q", content="a"),
        ],
        claims=claims,
        claim_evidence_qualifications=[
            ClaimEvidenceQualification(
                evidence_id="ev-a", is_primary_source=True
            )
        ],
        claim_gate_results=[
            gate_result(item, decision) for item, decision in zip(claims, decisions)
        ],
        generated_claim_records=[
            GeneratedClaimRecord(
                claim_id=claims[0].claim_id,
                rendered_text="Material fact",
                cited_evidence_ids=("ev-a", "ev-b"),
            )
        ],
        grounding_validation_results=[
            GroundingValidationResult(
                status=GroundingStatus.REPAIR_REQUIRED,
                repair_attempt=0,
            ),
            GroundingValidationResult(
                status=GroundingStatus.PASS,
                repair_attempt=1,
            ),
            GroundingValidationResult(
                status=GroundingStatus.FAIL,
                repair_attempt=1,
            ),
        ],
    )


def test_basic_multi_case_aggregation_and_latency_statistics():
    run = evaluate_run(
        metadata(),
        [completed_case("case-b", 3, contract=False), completed_case("case-a", 1)],
    )
    assert [case.case_id for case in run.cases] == ["case-a", "case-b"]
    assert run.summary.execution.model_dump() == {
        "total_cases": 2,
        "completed_cases": 2,
        "failed_cases": 0,
        "case_success_rate": 1.0,
    }
    assert run.summary.benchmark_contract.pass_count == 1
    assert run.summary.benchmark_contract.pass_rate == 0.5
    assert run.summary.benchmark_contract.required_unit_completion_rate == 0.75
    assert run.summary.efficiency.total_latency_seconds == 4
    assert run.summary.efficiency.mean_latency_seconds == 2
    assert run.summary.efficiency.median_latency_seconds == 2


def test_zero_case_zero_denominator_is_null_and_json_is_finite(tmp_path):
    run = evaluate_run(metadata(), [])
    assert run.summary.execution.case_success_rate is None
    assert run.summary.benchmark_contract.pass_rate is None
    assert run.summary.efficiency.mean_latency_seconds is None
    output = tmp_path / "run"
    write_run_artifacts(run, output)
    payload = (output / "evaluation.json").read_text(encoding="utf-8")
    assert "NaN" not in payload
    assert "Infinity" not in payload
    assert json.loads(payload)["summary"]["execution"]["case_success_rate"] is None


def test_adapter_aggregates_gate_grounding_evidence_and_pre_post_repair():
    case = EvaluationAdapter.from_structured_result(
        case_id="case-a",
        execution_status=ExecutionStatus.COMPLETED,
        evidence_context=structured_context(),
        claim_gate_available=True,
        grounding_available=True,
        supporting_source_authority_sum=1.6,
        supporting_source_count=2,
        repaired_claim_or_output_count=1,
    )
    assert case.evidence.selected_evidence_count == 2
    assert case.evidence.cited_evidence_count == 2
    assert case.evidence.qualified_primary_source_count == 1
    assert case.evidence.source_reliability_score == 0.8
    assert case.claim_gate.model_dump() == {
        "total_decisions": 4,
        "emit_count": 1,
        "hedge_count": 1,
        "omit_count": 1,
        "retrieve_more_count": 1,
        "material_claim_count": 3,
    }
    assert case.grounding.pass_count == 1
    assert case.grounding.repair_required_count == 1
    assert case.grounding.fail_count == 1
    assert case.grounding.pre_repair_violating_validation_count == 1
    assert case.grounding.post_repair_violating_validation_count == 1

    summary = evaluate_run(metadata(), [case]).summary
    assert summary.claim_gate.emit_count == 1
    assert summary.claim_gate.retrieve_more_count == 1
    assert summary.grounding.pre_repair_violating_validation_rate == 1.0
    assert summary.grounding.post_repair_violating_validation_rate == 0.5
    assert summary.grounding.repaired_claim_or_output_count == 1


def test_unavailable_structured_metrics_remain_unavailable():
    baseline = evaluate_run(metadata("baseline"), [completed_case("case-a", 1)])
    assert baseline.summary.evidence.selected_evidence_count is None
    assert baseline.summary.claim_gate.emit_count is None
    assert baseline.summary.grounding.pass_count is None
    assert baseline.summary.efficiency.input_tokens is None

    partial = evaluate_run(
        metadata("partial"),
        [
            completed_case("case-a", 1),
            EvaluationCaseResult(
                case_id="case-b",
                execution_status="completed",
                efficiency=EfficiencyCaseMetrics(latency_seconds=1),
            ),
        ],
    )
    assert partial.summary.benchmark_contract.evaluated_cases == 1
    assert partial.summary.benchmark_contract.pass_count is None
    assert partial.summary.benchmark_contract.pass_rate is None


def test_adapter_uses_metric_specific_availability_not_unrelated_stages():
    item = Claim(scope_id="case", normalized_text="Fact")
    context = EvidenceContext(
        context="fixture",
        claim_gate_results=[gate_result(item, ClaimGateDecision.EMIT)],
        grounding_validation_results=[
            GroundingValidationResult(status=GroundingStatus.PASS, repair_attempt=0)
        ],
    )
    case = EvaluationAdapter.from_structured_result(
        case_id="case-a",
        execution_status=ExecutionStatus.COMPLETED,
        evidence_context=context,
    )
    assert case.evidence is None
    assert case.claim_gate.total_decisions == 1
    assert case.grounding.pass_count == 1

    explicit_zero = EvaluationAdapter.from_structured_result(
        case_id="case-b",
        execution_status=ExecutionStatus.COMPLETED,
        evidence_context=EvidenceContext(context="fixture"),
        selected_evidence_available=True,
        generated_claim_records_available=True,
        evidence_qualifications_available=True,
        claim_gate_available=True,
        grounding_available=True,
    )
    assert explicit_zero.evidence.selected_evidence_count == 0
    assert explicit_zero.evidence.cited_evidence_count == 0
    assert explicit_zero.evidence.qualified_primary_source_count == 0
    assert explicit_zero.claim_gate.total_decisions == 0
    assert explicit_zero.grounding.total_validations == 0


def test_comparison_same_dataset_aligns_cases_and_calculates_deltas():
    run_a = evaluate_run(metadata("baseline"), [completed_case("case-a", 2)])
    run_b = evaluate_run(metadata("enterprise-v2"), [completed_case("case-a", 1)])
    comparison = compare_evaluation_runs(run_a, run_b)
    assert comparison.aligned_case_ids == ("case-a",)
    metrics = {metric.metric: metric for metric in comparison.metrics}
    assert metrics["efficiency.mean_latency_seconds"].delta_b_minus_a == -1
    assert metrics["execution.case_success_rate"].delta_b_minus_a == 0


def test_comparison_rejects_dataset_sha_mismatch():
    run_a = evaluate_run(metadata("baseline"), [completed_case("case-a", 1)])
    run_b = evaluate_run(
        metadata("enterprise-v2", dataset_sha="a" * 64),
        [completed_case("case-a", 1)],
    )
    with pytest.raises(ValueError, match="dataset SHA-256"):
        compare_evaluation_runs(run_a, run_b)


def test_comparison_detects_case_set_mismatch():
    run_a = evaluate_run(metadata("baseline"), [completed_case("case-a", 1)])
    run_b = evaluate_run(metadata("enterprise-v2"), [completed_case("case-b", 1)])
    with pytest.raises(ValueError, match="identical case sets"):
        compare_evaluation_runs(run_a, run_b)


def test_v2_only_metric_does_not_become_baseline_zero():
    baseline = evaluate_run(metadata("baseline"), [completed_case("case-a", 1)])
    v2_case = EvaluationAdapter.from_structured_result(
        case_id="case-a",
        execution_status=ExecutionStatus.COMPLETED,
        evidence_context=structured_context(),
        claim_gate_available=True,
        grounding_available=True,
        efficiency=EfficiencyCaseMetrics(latency_seconds=1),
    )
    v2 = evaluate_run(metadata("enterprise-v2"), [v2_case])
    comparison = compare_evaluation_runs(baseline, v2)
    metric = next(
        metric for metric in comparison.metrics if metric.metric == "claim_gate.emit_count"
    )
    assert metric.run_a is None
    assert metric.run_b == 1
    assert metric.delta_b_minus_a is None
    assert "| claim_gate.emit_count | N/A | 1 | N/A |" in render_comparison_markdown(
        comparison
    )


def test_comparison_writes_stable_json_and_markdown(tmp_path):
    run_a = evaluate_run(metadata("baseline"), [completed_case("case-a", 2)])
    run_b = evaluate_run(metadata("enterprise-v2"), [completed_case("case-a", 1)])
    comparison = compare_evaluation_runs(run_a, run_b)
    output = tmp_path / "comparison"
    write_comparison_artifacts(comparison, output)
    payload = (output / "comparison.json").read_text(encoding="utf-8")
    assert json.loads(payload)["aligned_case_ids"] == ["case-a"]
    assert "NaN" not in payload and "Infinity" not in payload
    assert "Delta (B - A)" in (output / "comparison.md").read_text(
        encoding="utf-8"
    )


def test_stable_output_ordering_and_no_overwrite(tmp_path):
    run = evaluate_run(
        metadata(), [completed_case("z-case", 1), completed_case("a-case", 1)]
    )
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_run_artifacts(run, first)
    write_run_artifacts(run, second)
    assert (first / "evaluation.json").read_bytes() == (
        second / "evaluation.json"
    ).read_bytes()
    assert (first / "summary.md").read_bytes() == (second / "summary.md").read_bytes()
    payload = json.loads((first / "evaluation.json").read_text(encoding="utf-8"))
    assert [case["case_id"] for case in payload["cases"]] == ["a-case", "z-case"]
    assert EvaluationRun.model_validate_json(
        (first / "evaluation.json").read_text(encoding="utf-8")
    ) == run
    with pytest.raises(FileExistsError):
        write_run_artifacts(run, first)


def test_failed_case_requires_bounded_error_and_secret_message_is_not_supported():
    case = EvaluationCaseResult(
        case_id="failed",
        execution_status="failed",
        error=EvaluationError(error_type="ProviderError", error_code="timeout"),
    )
    payload = case.model_dump_json()
    assert "ProviderError" in payload
    assert "message" not in payload
    with pytest.raises(ValueError, match="require bounded error"):
        EvaluationCaseResult(case_id="bad", execution_status="failed")
    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        EvaluationError(error_type="ProviderError", error_code="https://signed/url?key=x")
    with pytest.raises(ValueError, match="cannot pass"):
        EvaluationCaseResult(
            case_id="contradiction",
            execution_status="failed",
            benchmark_contract=BenchmarkContractCaseMetrics(passed=True),
            error=EvaluationError(error_type="ProviderError"),
        )
    with pytest.raises(ValueError, match="safe local reference"):
        EvaluationCaseResult(
            case_id="unsafe-trace-ref",
            execution_status="completed",
            trace_artifact_reference="https://signed.test/trace?token=secret",
        )
    with pytest.raises(ValueError, match="safe opaque identifier"):
        EvaluationCaseResult(
            case_id="unsafe-trace-id",
            execution_status="completed",
            trace_id="api_key:SECRET_VALUE",
        )


def test_frozen_benchmark_adapter_preserves_v22_contract_and_hash():
    data = load_frozen_v2_benchmark()
    assert data["schema_version"] == V2_BENCHMARK_SCHEMA_VERSION
    assert data["architecture_version"] == V2_ARCHITECTURE_VERSION
    assert len(data["cases"]) == 30
    assert all(case["required_units"] for case in data["cases"])
    frozen = metadata_for_frozen_v2(run_id="run", run_label="baseline")
    assert frozen.dataset_sha256 == V2_DATASET_SHA256
    assert frozen.source_commit is None
    assert frozen.model_identifier is None
    assert frozen.provider_identifier is None
    with pytest.raises(ValueError, match="Unknown case IDs"):
        evaluate_run(frozen, [completed_case("not-a-frozen-case", 1)])

    valid_case = completed_case(data["cases"][0]["id"], 1)
    assert evaluate_run(frozen, [valid_case]).cases[0].case_id == valid_case.case_id


def test_partial_latency_or_reliability_is_not_averaged_over_favorable_subset():
    context = structured_context()
    measured = EvaluationAdapter.from_structured_result(
        case_id="case-a",
        execution_status=ExecutionStatus.COMPLETED,
        evidence_context=context,
        efficiency=EfficiencyCaseMetrics(latency_seconds=1),
        supporting_source_authority_sum=0.8,
        supporting_source_count=1,
    )
    missing = EvaluationAdapter.from_structured_result(
        case_id="case-b",
        execution_status=ExecutionStatus.COMPLETED,
        evidence_context=context,
    )
    summary = evaluate_run(metadata(), [measured, missing]).summary
    assert summary.efficiency.latency_available_cases == 1
    assert summary.efficiency.mean_latency_seconds is None
    assert summary.evidence.source_reliability_score is None


def test_comparison_rejects_schema_mismatch():
    run_a = evaluate_run(metadata("baseline"), [completed_case("case-a", 1)])
    changed = metadata("enterprise-v2").model_copy(
        update={"benchmark_schema_version": "future/3"}
    )
    run_b = evaluate_run(changed, [completed_case("case-a", 1)])
    with pytest.raises(ValueError, match="benchmark schema"):
        compare_evaluation_runs(run_a, run_b)
