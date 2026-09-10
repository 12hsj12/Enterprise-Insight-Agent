"""Deterministic evaluation aggregation for frozen Enterprise Insight runs.

The harness consumes existing structured runtime records.  It does not execute
retrieval, run a judge, reinterpret Claim Gate decisions, or rerun grounding.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Annotated, Iterable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    field_validator,
    model_validator,
)

from gpt_researcher.evidence import EvidenceContext
from gpt_researcher.evidence.models import ClaimGateDecision, GroundingStatus


ROOT = Path(__file__).resolve().parents[1]
V2_DATASET = ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json"
V2_BENCHMARK_SCHEMA_VERSION = "enterprise-insight-bench-v2/2.2.0"
V2_ARCHITECTURE_VERSION = "enterprise-insight-v2-architecture/2.2.0"
V2_DATASET_SHA256 = (
    "95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa"
)

NonNegativeFloat = Annotated[FiniteFloat, Field(ge=0)]
UnitFloat = Annotated[FiniteFloat, Field(ge=0, le=1)]


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRunMetadata(EvaluationModel):
    run_id: str = Field(min_length=1)
    run_label: str = Field(min_length=1)
    architecture_version: str = Field(min_length=1)
    benchmark_schema_version: str = Field(min_length=1)
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_commit: str | None = None
    model_identifier: str | None = None
    provider_identifier: str | None = None
    benchmark_cutoff_date: date | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def timezone_is_explicit(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("evaluation timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def timing_is_ordered(self) -> "EvaluationRunMetadata":
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at precedes started_at")
        return self


class EvaluationError(EvaluationModel):
    """Bounded error metadata; provider messages are intentionally excluded."""

    error_type: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z_][A-Za-z0-9_.-]*$",
    )
    error_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )


class BenchmarkContractCaseMetrics(EvaluationModel):
    passed: bool | None = None
    required_units_satisfied: int | None = Field(default=None, ge=0)
    required_units_total: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def required_units_are_complete(self) -> "BenchmarkContractCaseMetrics":
        values = (self.required_units_satisfied, self.required_units_total)
        if (values[0] is None) != (values[1] is None):
            raise ValueError("required-unit numerator and denominator must appear together")
        if values[0] is not None and values[0] > values[1]:
            raise ValueError("satisfied required units exceed total required units")
        return self


class EvidenceCaseMetrics(EvaluationModel):
    selected_evidence_count: int | None = Field(default=None, ge=0)
    cited_evidence_count: int | None = Field(default=None, ge=0)
    qualified_primary_source_count: int | None = Field(default=None, ge=0)
    supporting_source_authority_sum: NonNegativeFloat | None = None
    supporting_source_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def reliability_components_are_complete(self) -> "EvidenceCaseMetrics":
        values = (self.supporting_source_authority_sum, self.supporting_source_count)
        if (values[0] is None) != (values[1] is None):
            raise ValueError("source-reliability numerator and denominator must appear together")
        if values[0] is not None and values[0] > values[1]:
            raise ValueError("authority sum cannot exceed supporting source count")
        return self

    @property
    def source_reliability_score(self) -> float | None:
        if not self.supporting_source_count:
            return None
        assert self.supporting_source_authority_sum is not None
        return self.supporting_source_authority_sum / self.supporting_source_count


class ClaimGateCaseMetrics(EvaluationModel):
    total_decisions: int = Field(ge=0)
    emit_count: int = Field(ge=0)
    hedge_count: int = Field(ge=0)
    omit_count: int = Field(ge=0)
    retrieve_more_count: int = Field(ge=0)
    material_claim_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def decisions_sum_to_total(self) -> "ClaimGateCaseMetrics":
        if self.total_decisions != (
            self.emit_count
            + self.hedge_count
            + self.omit_count
            + self.retrieve_more_count
        ):
            raise ValueError("Claim Gate decision counts do not sum to total")
        if (
            self.material_claim_count is not None
            and self.material_claim_count > self.total_decisions
        ):
            raise ValueError("material claims exceed gated claims")
        return self


class GroundingCaseMetrics(EvaluationModel):
    total_validations: int = Field(ge=0)
    pass_count: int = Field(ge=0)
    repair_required_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    pre_repair_validation_count: int = Field(ge=0)
    pre_repair_violating_validation_count: int = Field(ge=0)
    post_repair_validation_count: int = Field(ge=0)
    post_repair_violating_validation_count: int = Field(ge=0)
    repaired_claim_or_output_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def grounding_counts_are_consistent(self) -> "GroundingCaseMetrics":
        if self.total_validations != (
            self.pass_count + self.repair_required_count + self.fail_count
        ):
            raise ValueError("grounding status counts do not sum to total")
        if self.total_validations != (
            self.pre_repair_validation_count + self.post_repair_validation_count
        ):
            raise ValueError("grounding repair-stage counts do not sum to total")
        if (
            self.pre_repair_violating_validation_count
            > self.pre_repair_validation_count
        ):
            raise ValueError("pre-repair violating validations exceed validations")
        if (
            self.post_repair_violating_validation_count
            > self.post_repair_validation_count
        ):
            raise ValueError("post-repair violating validations exceed validations")
        return self


class EfficiencyCaseMetrics(EvaluationModel):
    latency_seconds: NonNegativeFloat | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: NonNegativeFloat | None = None


class EvaluationCaseResult(EvaluationModel):
    case_id: str = Field(min_length=1)
    execution_status: ExecutionStatus
    benchmark_contract: BenchmarkContractCaseMetrics = Field(
        default_factory=BenchmarkContractCaseMetrics
    )
    evidence: EvidenceCaseMetrics | None = None
    claim_gate: ClaimGateCaseMetrics | None = None
    grounding: GroundingCaseMetrics | None = None
    efficiency: EfficiencyCaseMetrics = Field(default_factory=EfficiencyCaseMetrics)
    error: EvaluationError | None = None
    artifact_reference: str | None = None
    trace_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )
    trace_artifact_reference: str | None = Field(default=None, max_length=500)

    @field_validator("trace_id")
    @classmethod
    def trace_id_is_public(cls, value: str | None) -> str | None:
        if value is not None and any(
            marker in value.lower()
            for marker in (
                "authorization",
                "bearer",
                "api_key",
                "api-key",
                "access_token",
                "access-token",
                "password",
                "secret",
            )
        ):
            raise ValueError("trace ID must be a safe opaque identifier")
        return value

    @field_validator("trace_artifact_reference")
    @classmethod
    def trace_reference_is_bounded(cls, value: str | None) -> str | None:
        if value is not None and (
            not value
            or any(ord(character) < 32 for character in value)
            or "://" in value
            or "?" in value
            or any(
                marker in value.lower()
                for marker in (
                    "authorization",
                    "bearer",
                    "api_key",
                    "api-key",
                    "access_token",
                    "access-token",
                    "password",
                    "secret",
                )
            )
        ):
            raise ValueError("trace artifact reference must be a safe local reference")
        return value

    @model_validator(mode="after")
    def error_matches_status(self) -> "EvaluationCaseResult":
        if self.execution_status is ExecutionStatus.FAILED and self.error is None:
            raise ValueError("failed cases require bounded error information")
        if self.execution_status is ExecutionStatus.COMPLETED and self.error is not None:
            raise ValueError("completed cases cannot contain execution errors")
        if self.execution_status is ExecutionStatus.FAILED:
            if self.benchmark_contract.passed is True:
                raise ValueError("failed cases cannot pass the benchmark contract")
            if self.benchmark_contract.required_units_satisfied not in (None, 0):
                raise ValueError("failed cases cannot satisfy required units")
        return self


class ExecutionSummary(EvaluationModel):
    total_cases: int = Field(ge=0)
    completed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    case_success_rate: UnitFloat | None = None


class BenchmarkContractSummary(EvaluationModel):
    evaluated_cases: int = Field(ge=0)
    pass_count: int | None = Field(default=None, ge=0)
    pass_rate: UnitFloat | None = None
    required_units_available_cases: int = Field(ge=0)
    required_units_satisfied: int | None = Field(default=None, ge=0)
    required_units_total: int | None = Field(default=None, ge=0)
    required_unit_completion_rate: UnitFloat | None = None


class EvidenceSummary(EvaluationModel):
    available_cases: int = Field(ge=0)
    selected_evidence_count: int | None = Field(default=None, ge=0)
    cited_evidence_count: int | None = Field(default=None, ge=0)
    qualified_primary_source_count: int | None = Field(default=None, ge=0)
    supporting_source_authority_sum: NonNegativeFloat | None = None
    supporting_source_count: int | None = Field(default=None, ge=0)
    source_reliability_score: UnitFloat | None = None


class ClaimGateSummary(EvaluationModel):
    available_cases: int = Field(ge=0)
    total_decisions: int | None = Field(default=None, ge=0)
    emit_count: int | None = Field(default=None, ge=0)
    hedge_count: int | None = Field(default=None, ge=0)
    omit_count: int | None = Field(default=None, ge=0)
    retrieve_more_count: int | None = Field(default=None, ge=0)
    material_claim_count: int | None = Field(default=None, ge=0)


class GroundingSummary(EvaluationModel):
    available_cases: int = Field(ge=0)
    total_validations: int | None = Field(default=None, ge=0)
    pass_count: int | None = Field(default=None, ge=0)
    repair_required_count: int | None = Field(default=None, ge=0)
    fail_count: int | None = Field(default=None, ge=0)
    pre_repair_validation_count: int | None = Field(default=None, ge=0)
    pre_repair_violating_validation_count: int | None = Field(default=None, ge=0)
    pre_repair_violating_validation_rate: UnitFloat | None = None
    post_repair_validation_count: int | None = Field(default=None, ge=0)
    post_repair_violating_validation_count: int | None = Field(default=None, ge=0)
    post_repair_violating_validation_rate: UnitFloat | None = None
    repaired_claim_or_output_count: int | None = Field(default=None, ge=0)


class EfficiencySummary(EvaluationModel):
    latency_available_cases: int = Field(ge=0)
    total_latency_seconds: NonNegativeFloat | None = None
    mean_latency_seconds: NonNegativeFloat | None = None
    median_latency_seconds: NonNegativeFloat | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: NonNegativeFloat | None = None


class EvaluationSummary(EvaluationModel):
    execution: ExecutionSummary
    benchmark_contract: BenchmarkContractSummary
    evidence: EvidenceSummary
    claim_gate: ClaimGateSummary
    grounding: GroundingSummary
    efficiency: EfficiencySummary


class EvaluationRun(EvaluationModel):
    metadata: EvaluationRunMetadata
    cases: tuple[EvaluationCaseResult, ...]
    summary: EvaluationSummary

    @model_validator(mode="after")
    def cases_are_unique_sorted_and_summary_matches(self) -> "EvaluationRun":
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("evaluation case IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("evaluation cases must use stable case_id ordering")
        _validate_case_membership(self.metadata, self.cases)
        if self.summary != aggregate_cases(self.cases):
            raise ValueError("stored evaluation summary does not match case results")
        return self


class MetricComparison(EvaluationModel):
    metric: str
    run_a: FiniteFloat | int | None
    run_b: FiniteFloat | int | None
    delta_b_minus_a: FiniteFloat | None


class EvaluationComparison(EvaluationModel):
    run_a_id: str
    run_a_label: str
    run_b_id: str
    run_b_label: str
    benchmark_schema_version: str
    dataset_sha256: str
    aligned_case_ids: tuple[str, ...]
    metrics: tuple[MetricComparison, ...]


def load_frozen_v2_benchmark() -> dict:
    """Load and verify the existing frozen V2.2 dataset without changing it."""

    raw = V2_DATASET.read_bytes()
    if hashlib.sha256(raw).hexdigest() != V2_DATASET_SHA256:
        raise ValueError("Frozen V2 dataset SHA-256 mismatch")
    data = json.loads(raw)
    if data.get("schema_version") != V2_BENCHMARK_SCHEMA_VERSION:
        raise ValueError("Frozen V2 benchmark schema version mismatch")
    if data.get("architecture_version") != V2_ARCHITECTURE_VERSION:
        raise ValueError("Frozen V2 architecture version mismatch")
    cases = data.get("cases", [])
    if len(cases) != 30 or len({case["id"] for case in cases}) != 30:
        raise ValueError("Frozen V2 benchmark must contain 30 unique cases")
    return data


def metadata_for_frozen_v2(
    *,
    run_id: str,
    run_label: str,
    source_commit: str | None = None,
    model_identifier: str | None = None,
    provider_identifier: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> EvaluationRunMetadata:
    data = load_frozen_v2_benchmark()
    return EvaluationRunMetadata(
        run_id=run_id,
        run_label=run_label,
        architecture_version=data["architecture_version"],
        benchmark_schema_version=data["schema_version"],
        dataset_sha256=V2_DATASET_SHA256,
        source_commit=source_commit,
        model_identifier=model_identifier,
        provider_identifier=provider_identifier,
        benchmark_cutoff_date=data.get("cutoff_date"),
        started_at=started_at,
        completed_at=completed_at,
    )


class EvaluationAdapter:
    """Adapt existing evidence/gate/grounding records into one case result."""

    @staticmethod
    def from_structured_result(
        *,
        case_id: str,
        execution_status: ExecutionStatus,
        evidence_context: EvidenceContext | None = None,
        benchmark_contract: BenchmarkContractCaseMetrics | None = None,
        efficiency: EfficiencyCaseMetrics | None = None,
        error: EvaluationError | None = None,
        artifact_reference: str | None = None,
        trace_id: str | None = None,
        trace_artifact_reference: str | None = None,
        selected_evidence_available: bool | None = None,
        generated_claim_records_available: bool | None = None,
        evidence_qualifications_available: bool | None = None,
        claim_gate_available: bool | None = None,
        grounding_available: bool | None = None,
        supporting_source_authority_sum: float | None = None,
        supporting_source_count: int | None = None,
        repaired_claim_or_output_count: int | None = None,
    ) -> EvaluationCaseResult:
        context = evidence_context
        evidence_metrics = None
        gate_metrics = None
        grounding_metrics = None
        if context is not None:
            gate_available = (
                bool(context.claim_gate_results)
                if claim_gate_available is None
                else claim_gate_available
            )
            ground_available = (
                bool(context.grounding_validation_results)
                if grounding_available is None
                else grounding_available
            )
            selection_available = (
                bool(context.evidences)
                if selected_evidence_available is None
                else selected_evidence_available
            )
            claim_records_available = (
                bool(context.generated_claim_records)
                if generated_claim_records_available is None
                else generated_claim_records_available
            )
            qualifications_available = (
                bool(context.claim_evidence_qualifications)
                if evidence_qualifications_available is None
                else evidence_qualifications_available
            )
            cited_ids = {
                evidence_id
                for record in context.generated_claim_records
                for evidence_id in record.cited_evidence_ids
            }
            primary_count = (
                len(
                    {
                        qualification.evidence_id
                        for qualification in context.claim_evidence_qualifications
                        if qualification.is_primary_source is True
                    }
                )
                if qualifications_available
                else None
            )
            if (
                selection_available
                or claim_records_available
                or qualifications_available
                or supporting_source_authority_sum is not None
                or supporting_source_count is not None
            ):
                evidence_metrics = EvidenceCaseMetrics(
                    selected_evidence_count=(
                        len({evidence.evidence_id for evidence in context.evidences})
                        if selection_available
                        else None
                    ),
                    cited_evidence_count=(
                        len(cited_ids) if claim_records_available else None
                    ),
                    qualified_primary_source_count=primary_count,
                    supporting_source_authority_sum=supporting_source_authority_sum,
                    supporting_source_count=supporting_source_count,
                )
            if gate_available:
                decision_counts = {
                    decision: sum(
                        result.decision is decision
                        for result in context.claim_gate_results
                    )
                    for decision in ClaimGateDecision
                }
                claims_by_id = {claim.claim_id: claim for claim in context.claims}
                gate_ids = {result.claim_id for result in context.claim_gate_results}
                material_count = (
                    sum(claims_by_id[claim_id].is_material for claim_id in gate_ids)
                    if gate_ids.issubset(claims_by_id)
                    else None
                )
                gate_metrics = ClaimGateCaseMetrics(
                    total_decisions=len(context.claim_gate_results),
                    emit_count=decision_counts[ClaimGateDecision.EMIT],
                    hedge_count=decision_counts[ClaimGateDecision.HEDGE],
                    omit_count=decision_counts[ClaimGateDecision.OMIT],
                    retrieve_more_count=decision_counts[
                        ClaimGateDecision.RETRIEVE_MORE
                    ],
                    material_claim_count=material_count,
                )
            if ground_available:
                results = context.grounding_validation_results
                pre = [result for result in results if result.repair_attempt == 0]
                post = [result for result in results if result.repair_attempt == 1]
                grounding_metrics = GroundingCaseMetrics(
                    total_validations=len(results),
                    pass_count=sum(
                        result.status is GroundingStatus.PASS for result in results
                    ),
                    repair_required_count=sum(
                        result.status is GroundingStatus.REPAIR_REQUIRED
                        for result in results
                    ),
                    fail_count=sum(
                        result.status is GroundingStatus.FAIL for result in results
                    ),
                    pre_repair_validation_count=len(pre),
                    pre_repair_violating_validation_count=sum(
                        result.status is not GroundingStatus.PASS for result in pre
                    ),
                    post_repair_validation_count=len(post),
                    post_repair_violating_validation_count=sum(
                        result.status is not GroundingStatus.PASS for result in post
                    ),
                    repaired_claim_or_output_count=repaired_claim_or_output_count,
                )
        elif (
            any(
                value is True
                for value in (
                    selected_evidence_available,
                    generated_claim_records_available,
                    evidence_qualifications_available,
                    claim_gate_available,
                    grounding_available,
                )
            )
            or supporting_source_authority_sum is not None
            or supporting_source_count is not None
            or repaired_claim_or_output_count is not None
        ):
            raise ValueError("structured metric availability requires evidence context")

        return EvaluationCaseResult(
            case_id=case_id,
            execution_status=execution_status,
            benchmark_contract=benchmark_contract or BenchmarkContractCaseMetrics(),
            evidence=evidence_metrics,
            claim_gate=gate_metrics,
            grounding=grounding_metrics,
            efficiency=efficiency or EfficiencyCaseMetrics(),
            error=error,
            artifact_reference=artifact_reference,
            trace_id=trace_id,
            trace_artifact_reference=trace_artifact_reference,
        )


def _complete_sum(values: Iterable[int | float | None]) -> int | float | None:
    materialized = list(values)
    if not materialized or any(value is None for value in materialized):
        return None
    return sum(materialized)  # type: ignore[arg-type]


def _safe_rate(numerator: int | float | None, denominator: int | float | None):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def aggregate_cases(cases: Iterable[EvaluationCaseResult]) -> EvaluationSummary:
    ordered = sorted(cases, key=lambda case: case.case_id)
    if len({case.case_id for case in ordered}) != len(ordered):
        raise ValueError("evaluation case IDs must be unique")
    completed = [
        case for case in ordered if case.execution_status is ExecutionStatus.COMPLETED
    ]

    contract_values = [case.benchmark_contract.passed for case in ordered]
    contract_results = [value for value in contract_values if value is not None]
    required_available = [
        case.benchmark_contract
        for case in ordered
        if case.benchmark_contract.required_units_total is not None
    ]
    required_satisfied = _complete_sum(
        case.benchmark_contract.required_units_satisfied for case in ordered
    )
    required_total = _complete_sum(
        case.benchmark_contract.required_units_total for case in ordered
    )

    evidence_cases = [case.evidence for case in completed if case.evidence is not None]
    selected = _complete_sum(
        case.evidence.selected_evidence_count if case.evidence else None
        for case in completed
    )
    cited = _complete_sum(
        case.evidence.cited_evidence_count if case.evidence else None
        for case in completed
    )
    primary = _complete_sum(
        case.evidence.qualified_primary_source_count if case.evidence else None
        for case in completed
    )
    authority_sum = _complete_sum(
        case.evidence.supporting_source_authority_sum if case.evidence else None
        for case in completed
    )
    supporting_sources = _complete_sum(
        case.evidence.supporting_source_count if case.evidence else None
        for case in completed
    )

    gate_cases = [case.claim_gate for case in completed if case.claim_gate is not None]
    grounding_cases = [
        case.grounding for case in completed if case.grounding is not None
    ]

    latencies = [case.efficiency.latency_seconds for case in ordered]
    all_latency_available = bool(latencies) and all(value is not None for value in latencies)
    known_latencies = [float(value) for value in latencies if value is not None]

    total = len(ordered)
    completed_count = len(completed)
    failed_count = total - completed_count
    contract_passes = _complete_sum(contract_values)

    gate = ClaimGateSummary(
        available_cases=len(gate_cases),
        total_decisions=_complete_sum(
            case.claim_gate.total_decisions if case.claim_gate else None
            for case in completed
        ),
        emit_count=_complete_sum(
            case.claim_gate.emit_count if case.claim_gate else None for case in completed
        ),
        hedge_count=_complete_sum(
            case.claim_gate.hedge_count if case.claim_gate else None for case in completed
        ),
        omit_count=_complete_sum(
            case.claim_gate.omit_count if case.claim_gate else None for case in completed
        ),
        retrieve_more_count=_complete_sum(
            case.claim_gate.retrieve_more_count if case.claim_gate else None
            for case in completed
        ),
        material_claim_count=_complete_sum(
            case.claim_gate.material_claim_count if case.claim_gate else None
            for case in completed
        ),
    )

    grounding_values = {
        field: _complete_sum(
            getattr(case.grounding, field) if case.grounding else None
            for case in completed
        )
        for field in (
            "total_validations",
            "pass_count",
            "repair_required_count",
            "fail_count",
            "pre_repair_validation_count",
            "pre_repair_violating_validation_count",
            "post_repair_validation_count",
            "post_repair_violating_validation_count",
            "repaired_claim_or_output_count",
        )
    }

    input_tokens = _complete_sum(case.efficiency.input_tokens for case in ordered)
    output_tokens = _complete_sum(case.efficiency.output_tokens for case in ordered)
    costs = _complete_sum(case.efficiency.estimated_cost_usd for case in ordered)

    return EvaluationSummary(
        execution=ExecutionSummary(
            total_cases=total,
            completed_cases=completed_count,
            failed_cases=failed_count,
            case_success_rate=_safe_rate(completed_count, total),
        ),
        benchmark_contract=BenchmarkContractSummary(
            evaluated_cases=len(contract_results),
            pass_count=contract_passes,
            pass_rate=_safe_rate(contract_passes, len(contract_results)),
            required_units_available_cases=len(required_available),
            required_units_satisfied=required_satisfied,
            required_units_total=required_total,
            required_unit_completion_rate=_safe_rate(required_satisfied, required_total),
        ),
        evidence=EvidenceSummary(
            available_cases=len(evidence_cases),
            selected_evidence_count=selected,
            cited_evidence_count=cited,
            qualified_primary_source_count=primary,
            supporting_source_authority_sum=authority_sum,
            supporting_source_count=supporting_sources,
            source_reliability_score=_safe_rate(authority_sum, supporting_sources),
        ),
        claim_gate=gate,
        grounding=GroundingSummary(
            available_cases=len(grounding_cases),
            total_validations=grounding_values["total_validations"],
            pass_count=grounding_values["pass_count"],
            repair_required_count=grounding_values["repair_required_count"],
            fail_count=grounding_values["fail_count"],
            pre_repair_validation_count=grounding_values[
                "pre_repair_validation_count"
            ],
            pre_repair_violating_validation_count=grounding_values[
                "pre_repair_violating_validation_count"
            ],
            pre_repair_violating_validation_rate=_safe_rate(
                grounding_values["pre_repair_violating_validation_count"],
                grounding_values["pre_repair_validation_count"],
            ),
            post_repair_validation_count=grounding_values[
                "post_repair_validation_count"
            ],
            post_repair_violating_validation_count=grounding_values[
                "post_repair_violating_validation_count"
            ],
            post_repair_violating_validation_rate=_safe_rate(
                grounding_values["post_repair_violating_validation_count"],
                grounding_values["post_repair_validation_count"],
            ),
            repaired_claim_or_output_count=grounding_values[
                "repaired_claim_or_output_count"
            ],
        ),
        efficiency=EfficiencySummary(
            latency_available_cases=len(known_latencies),
            total_latency_seconds=(sum(known_latencies) if all_latency_available else None),
            mean_latency_seconds=(
                sum(known_latencies) / len(known_latencies)
                if all_latency_available
                else None
            ),
            median_latency_seconds=(
                median(known_latencies) if all_latency_available else None
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=costs,
        ),
    )


def evaluate_run(
    metadata: EvaluationRunMetadata,
    cases: Iterable[EvaluationCaseResult],
) -> EvaluationRun:
    ordered = tuple(sorted(cases, key=lambda case: case.case_id))

    return EvaluationRun(
        metadata=metadata,
        cases=ordered,
        summary=aggregate_cases(ordered),
    )


def _validate_case_membership(
    metadata: EvaluationRunMetadata,
    cases: Iterable[EvaluationCaseResult],
) -> None:
    identifies_frozen_v2 = (
        metadata.benchmark_schema_version == V2_BENCHMARK_SCHEMA_VERSION
        or metadata.dataset_sha256 == V2_DATASET_SHA256
    )
    if identifies_frozen_v2:
        if metadata.benchmark_schema_version != V2_BENCHMARK_SCHEMA_VERSION:
            raise ValueError("Frozen V2 dataset requires its frozen benchmark schema")
        if metadata.dataset_sha256 != V2_DATASET_SHA256:
            raise ValueError("Frozen V2 benchmark schema requires its frozen dataset SHA-256")
        frozen_case_ids = {
            case["id"] for case in load_frozen_v2_benchmark()["cases"]
        }
        unknown_case_ids = sorted(
            {case.case_id for case in cases} - frozen_case_ids
        )
        if unknown_case_ids:
            raise ValueError(
                f"Unknown case IDs for frozen V2 dataset: {unknown_case_ids}"
            )


COMPARISON_METRICS = (
    "execution.total_cases",
    "execution.completed_cases",
    "execution.failed_cases",
    "execution.case_success_rate",
    "benchmark_contract.pass_count",
    "benchmark_contract.pass_rate",
    "benchmark_contract.required_units_satisfied",
    "benchmark_contract.required_units_total",
    "benchmark_contract.required_unit_completion_rate",
    "evidence.selected_evidence_count",
    "evidence.cited_evidence_count",
    "evidence.qualified_primary_source_count",
    "evidence.source_reliability_score",
    "claim_gate.total_decisions",
    "claim_gate.emit_count",
    "claim_gate.hedge_count",
    "claim_gate.omit_count",
    "claim_gate.retrieve_more_count",
    "claim_gate.material_claim_count",
    "grounding.total_validations",
    "grounding.pass_count",
    "grounding.repair_required_count",
    "grounding.fail_count",
    "grounding.pre_repair_violating_validation_count",
    "grounding.pre_repair_violating_validation_rate",
    "grounding.post_repair_violating_validation_count",
    "grounding.post_repair_violating_validation_rate",
    "grounding.repaired_claim_or_output_count",
    "efficiency.total_latency_seconds",
    "efficiency.mean_latency_seconds",
    "efficiency.median_latency_seconds",
    "efficiency.input_tokens",
    "efficiency.output_tokens",
    "efficiency.estimated_cost_usd",
)


def _metric_value(summary: EvaluationSummary, path: str):
    section_name, field_name = path.split(".", 1)
    return getattr(getattr(summary, section_name), field_name)


def compare_evaluation_runs(
    run_a: EvaluationRun,
    run_b: EvaluationRun,
) -> EvaluationComparison:
    if run_a.metadata.dataset_sha256 != run_b.metadata.dataset_sha256:
        raise ValueError("evaluation comparison requires identical dataset SHA-256")
    if (
        run_a.metadata.benchmark_schema_version
        != run_b.metadata.benchmark_schema_version
    ):
        raise ValueError("evaluation comparison requires identical benchmark schema version")
    ids_a = tuple(case.case_id for case in run_a.cases)
    ids_b = tuple(case.case_id for case in run_b.cases)
    if ids_a != ids_b:
        missing_from_b = sorted(set(ids_a) - set(ids_b))
        missing_from_a = sorted(set(ids_b) - set(ids_a))
        raise ValueError(
            "evaluation comparison requires identical case sets; "
            f"missing_from_a={missing_from_a}, missing_from_b={missing_from_b}"
        )

    comparisons = []
    for metric in COMPARISON_METRICS:
        value_a = _metric_value(run_a.summary, metric)
        value_b = _metric_value(run_b.summary, metric)
        delta = None if value_a is None or value_b is None else value_b - value_a
        comparisons.append(
            MetricComparison(
                metric=metric,
                run_a=value_a,
                run_b=value_b,
                delta_b_minus_a=delta,
            )
        )
    return EvaluationComparison(
        run_a_id=run_a.metadata.run_id,
        run_a_label=run_a.metadata.run_label,
        run_b_id=run_b.metadata.run_id,
        run_b_label=run_b.metadata.run_label,
        benchmark_schema_version=run_a.metadata.benchmark_schema_version,
        dataset_sha256=run_a.metadata.dataset_sha256,
        aligned_case_ids=ids_a,
        metrics=tuple(comparisons),
    )


def _json_text(model: BaseModel) -> str:
    value = model.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _display(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _escape(value) -> str:
    return _display(value).replace("|", "\\|").replace("\n", " ")


def render_run_markdown(run: EvaluationRun) -> str:
    metadata = run.metadata
    summary = run.summary
    lines = [
        f"# Evaluation Run: {_escape(metadata.run_label)}",
        "",
        "## Run metadata",
        "",
        "| Field | Value |",
        "|---|---|",
    ]
    for name in EvaluationRunMetadata.model_fields:
        lines.append(f"| {name} | {_escape(getattr(metadata, name))} |")

    lines.extend(["", "## Core metrics", "", "| Metric | Value |", "|---|---:|"])
    for metric in COMPARISON_METRICS:
        lines.append(f"| {metric} | {_escape(_metric_value(summary, metric))} |")

    lines.extend(
        [
            "",
            "Unavailable values are shown as `N/A`; they are never imputed as zero.",
            "Claim Gate decision rates are intentionally omitted because their direction "
            "is not a quality score.",
            "",
            "## Per-case results",
            "",
            "| Case | Status | Contract | Latency (s) | Selected | Cited | "
            "Gate (E/H/O/R) | Grounding (P/R/F) | Error |",
            "|---|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for case in run.cases:
        evidence = case.evidence
        gate = case.claim_gate
        grounding = case.grounding
        gate_display = (
            f"{gate.emit_count}/{gate.hedge_count}/{gate.omit_count}/{gate.retrieve_more_count}"
            if gate is not None
            else "N/A"
        )
        grounding_display = (
            f"{grounding.pass_count}/{grounding.repair_required_count}/{grounding.fail_count}"
            if grounding is not None
            else "N/A"
        )
        lines.append(
            "| "
            + " | ".join(
                _escape(value)
                for value in (
                    case.case_id,
                    case.execution_status.value,
                    case.benchmark_contract.passed,
                    case.efficiency.latency_seconds,
                    evidence.selected_evidence_count if evidence else None,
                    evidence.cited_evidence_count if evidence else None,
                    gate_display,
                    grounding_display,
                    case.error.error_type if case.error else None,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_comparison_markdown(comparison: EvaluationComparison) -> str:
    lines = [
        f"# Evaluation Comparison: {_escape(comparison.run_a_label)} vs "
        f"{_escape(comparison.run_b_label)}",
        "",
        f"Dataset SHA-256: `{comparison.dataset_sha256}`",
        "",
        f"Benchmark schema: `{comparison.benchmark_schema_version}`",
        "",
        f"Aligned cases: {len(comparison.aligned_case_ids)}",
        "",
        "| Metric | Run A | Run B | Delta (B - A) |",
        "|---|---:|---:|---:|",
    ]
    for metric in comparison.metrics:
        lines.append(
            f"| {_escape(metric.metric)} | {_escape(metric.run_a)} | "
            f"{_escape(metric.run_b)} | {_escape(metric.delta_b_minus_a)} |"
        )
    lines.extend(
        [
            "",
            "A delta is calculated only when both runs provide the metric; otherwise it is `N/A`.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_run_artifacts(run: EvaluationRun, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "evaluation.json").write_text(_json_text(run), encoding="utf-8")
    (output / "summary.md").write_text(render_run_markdown(run), encoding="utf-8")


def write_comparison_artifacts(
    comparison: EvaluationComparison,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "comparison.json").write_text(
        _json_text(comparison), encoding="utf-8"
    )
    (output / "comparison.md").write_text(
        render_comparison_markdown(comparison), encoding="utf-8"
    )


def _read_model(path: Path, model_type):
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="aggregate typed case results")
    run_parser.add_argument("--metadata", type=Path, required=True)
    run_parser.add_argument("--cases", type=Path, required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    compare_parser = commands.add_parser("compare", help="compare two evaluation runs")
    compare_parser.add_argument("--run-a", type=Path, required=True)
    compare_parser.add_argument("--run-b", type=Path, required=True)
    compare_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "run":
        metadata = _read_model(args.metadata, EvaluationRunMetadata)
        raw_cases = json.loads(args.cases.read_text(encoding="utf-8"))
        cases = [EvaluationCaseResult.model_validate(case) for case in raw_cases]
        write_run_artifacts(evaluate_run(metadata, cases), args.output)
    else:
        run_a = _read_model(args.run_a, EvaluationRun)
        run_b = _read_model(args.run_b, EvaluationRun)
        write_comparison_artifacts(
            compare_evaluation_runs(run_a, run_b), args.output
        )


if __name__ == "__main__":
    main()
