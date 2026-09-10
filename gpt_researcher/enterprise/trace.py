"""Bounded, local, observation-only research execution traces.

The recorder accepts structured results that the pipeline already produced. It
never re-runs ranking, Claim Gate, grounding validation, or repair logic, and it
excludes query text, evidence content, URLs, prompts, and exception messages.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
import time
from typing import Annotated, Literal, Union
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    field_validator,
    model_validator,
)

from gpt_researcher.evidence.models import (
    Claim,
    ClaimGateDecision,
    ClaimGateResult,
    ClaimRiskType,
    EvidenceStrengthRule,
    GeneratedClaimRecord,
    GroundingFindingCode,
    GroundingRepairOperation,
    GroundingRepairPlan,
    GroundingStatus,
    GroundingValidationResult,
)


MAX_TRACE_EVENTS = 1000
MAX_EVENT_IDS = 100
DEFAULT_TRACE_DIRECTORY = Path("outputs/traces")


class TraceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchExecutionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchTraceEventType(str, Enum):
    RESEARCH_STARTED = "research_started"
    EVIDENCE_SELECTION = "evidence_selection"
    CLAIM_GATE = "claim_gate"
    GENERATION = "generation"
    GROUNDING_VALIDATION = "grounding_validation"
    REPAIR = "repair"
    RESEARCH_COMPLETED = "research_completed"


class ClaimGateTracePhase(str, Enum):
    PRE_GENERATION = "pre_generation"
    GROUNDING_REVALIDATION = "grounding_revalidation"


def _validate_reference(value: str | None) -> str | None:
    if value is None:
        return None
    sensitive = re.search(
        r"authorization|bearer|api[_-]?key|access[_-]?token|password|secret",
        value,
        flags=re.IGNORECASE,
    )
    if (
        not value
        or len(value) > 500
        or any(ord(char) < 32 for char in value)
        or "://" in value
        or "?" in value
        or sensitive
    ):
        raise ValueError("trace references must be non-empty, bounded, and single-line")
    return value


def _validate_id(value: str | None, *, label: str, max_length: int) -> str | None:
    if value is None:
        return None
    if (
        not value
        or len(value) > max_length
        or re.fullmatch(r"[A-Za-z0-9_.:-]+", value) is None
        or re.search(
            r"authorization|bearer|api[_-]?key|access[_-]?token|password|secret",
            value,
            flags=re.IGNORECASE,
        )
    ):
        raise ValueError(f"{label} must be a bounded opaque identifier")
    return value


def _sanitized_id(value: str, *, label: str, max_length: int = 200) -> str:
    try:
        validated = _validate_id(value, label=label, max_length=max_length)
        assert validated is not None
        return validated
    except (AssertionError, TypeError, ValueError):
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        prefix = "redacted_"
        return prefix + digest[: max_length - len(prefix)]


def _sanitized_reference(value: str | None) -> str | None:
    try:
        return _validate_reference(value)
    except (TypeError, ValueError):
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        return f"redacted_ref_{digest}"


class TraceErrorMetadata(TraceModel):
    """Bounded failure identity; exception messages are intentionally excluded."""

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

    @field_validator("error_code")
    @classmethod
    def error_code_is_public(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_id(value, label="error_code", max_length=64)
        return value


class ResearchTraceEvent(TraceModel):
    sequence: int = Field(ge=0)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def timezone_is_explicit(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("trace event timestamps must include a timezone")
        return value


class ResearchStartedEvent(ResearchTraceEvent):
    event_type: Literal[ResearchTraceEventType.RESEARCH_STARTED] = (
        ResearchTraceEventType.RESEARCH_STARTED
    )


class RetrievalScoreTrace(TraceModel):
    """Existing ranking components only; no source payload or URL is retained."""

    evidence_id: str = Field(min_length=1, max_length=200)
    similarity_score: FiniteFloat
    authority_score: FiniteFloat
    final_score: FiniteFloat

    @field_validator("evidence_id")
    @classmethod
    def evidence_id_is_public(cls, value: str) -> str:
        return _validate_id(value, label="evidence_id", max_length=200)  # type: ignore[return-value]


class EvidenceSelectionEvent(ResearchTraceEvent):
    event_type: Literal[ResearchTraceEventType.EVIDENCE_SELECTION] = (
        ResearchTraceEventType.EVIDENCE_SELECTION
    )
    task_category: str | None = Field(default=None, max_length=100)
    candidate_evidence_count: int | None = Field(default=None, ge=0)
    selected_evidence_count: int = Field(ge=0)
    authority_weight: FiniteFloat | None = Field(default=None, ge=0, le=1)
    similarity_threshold: FiniteFloat | None = None
    selected_evidence_ids: tuple[str, ...] = Field(default=(), max_length=MAX_EVENT_IDS)
    scorer_summary: tuple[RetrievalScoreTrace, ...] = Field(
        default=(), max_length=MAX_EVENT_IDS
    )

    @field_validator("selected_evidence_ids")
    @classmethod
    def selected_ids_are_public(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            _validate_id(value, label="evidence_id", max_length=200)  # type: ignore[misc]
            for value in values
        )


class ClaimGateEvent(ResearchTraceEvent):
    event_type: Literal[ResearchTraceEventType.CLAIM_GATE] = (
        ResearchTraceEventType.CLAIM_GATE
    )
    claim_id: str = Field(min_length=1, max_length=200)
    phase: ClaimGateTracePhase
    risk_types: tuple[ClaimRiskType, ...] = Field(default=(), max_length=20)
    is_material: bool
    evidence_strength_rules: tuple[EvidenceStrengthRule, ...] = Field(
        min_length=1, max_length=20
    )
    required_entity_ids: tuple[str, ...] = Field(default=(), max_length=MAX_EVENT_IDS)
    required_material_side_ids: tuple[str, ...] = Field(
        default=(), max_length=MAX_EVENT_IDS
    )
    requires_independent_adjudicator: bool
    gate_decision: ClaimGateDecision

    @field_validator("claim_id")
    @classmethod
    def claim_id_is_public(cls, value: str) -> str:
        return _validate_id(value, label="claim_id", max_length=200)  # type: ignore[return-value]

    @field_validator("required_entity_ids", "required_material_side_ids")
    @classmethod
    def obligation_ids_are_public(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            _validate_id(value, label="obligation_id", max_length=200)  # type: ignore[misc]
            for value in values
        )


class GenerationEvent(ResearchTraceEvent):
    event_type: Literal[ResearchTraceEventType.GENERATION] = (
        ResearchTraceEventType.GENERATION
    )
    generated_claim_count: int | None = Field(default=None, ge=0)
    generated_claim_ids: tuple[str, ...] = Field(default=(), max_length=MAX_EVENT_IDS)
    output_artifact_reference: str | None = None

    _validate_artifact_reference = field_validator("output_artifact_reference")(
        _validate_reference
    )

    @field_validator("generated_claim_ids")
    @classmethod
    def generated_ids_are_public(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            _validate_id(value, label="claim_id", max_length=200)  # type: ignore[misc]
            for value in values
        )


class GroundingValidationEvent(ResearchTraceEvent):
    event_type: Literal[ResearchTraceEventType.GROUNDING_VALIDATION] = (
        ResearchTraceEventType.GROUNDING_VALIDATION
    )
    claim_id: str = Field(min_length=1, max_length=200)
    grounding_status: GroundingStatus
    finding_codes: tuple[GroundingFindingCode, ...] = Field(
        default=(), max_length=50
    )
    cited_evidence_count: int = Field(ge=0)
    repair_required: bool
    failed: bool
    planned_repair_action_types: tuple[GroundingRepairOperation, ...] = Field(
        default=(), max_length=20
    )

    @field_validator("claim_id")
    @classmethod
    def claim_id_is_public(cls, value: str) -> str:
        return _validate_id(value, label="claim_id", max_length=200)  # type: ignore[return-value]


class RepairEvent(ResearchTraceEvent):
    event_type: Literal[ResearchTraceEventType.REPAIR] = ResearchTraceEventType.REPAIR
    claim_id: str = Field(min_length=1, max_length=200)
    action_type: GroundingRepairOperation
    evidence_id: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("claim_id", "evidence_id")
    @classmethod
    def repair_ids_are_public(cls, value: str | None) -> str | None:
        return _validate_id(value, label="repair_id", max_length=200)


class ResearchCompletedEvent(ResearchTraceEvent):
    event_type: Literal[ResearchTraceEventType.RESEARCH_COMPLETED] = (
        ResearchTraceEventType.RESEARCH_COMPLETED
    )
    execution_status: Literal[
        ResearchExecutionStatus.COMPLETED, ResearchExecutionStatus.FAILED
    ]
    total_duration_seconds: FiniteFloat | None = Field(default=None, ge=0)
    final_claim_count: int | None = Field(default=None, ge=0)
    output_artifact_reference: str | None = None
    error: TraceErrorMetadata | None = None

    _validate_artifact_reference = field_validator("output_artifact_reference")(
        _validate_reference
    )

    @model_validator(mode="after")
    def error_matches_status(self) -> "ResearchCompletedEvent":
        if self.execution_status is ResearchExecutionStatus.FAILED and self.error is None:
            raise ValueError("failed completion events require bounded error metadata")
        if self.execution_status is ResearchExecutionStatus.COMPLETED and self.error:
            raise ValueError("completed events cannot contain an error")
        return self


TraceEvent = Annotated[
    Union[
        ResearchStartedEvent,
        EvidenceSelectionEvent,
        ClaimGateEvent,
        GenerationEvent,
        GroundingValidationEvent,
        RepairEvent,
        ResearchCompletedEvent,
    ],
    Field(discriminator="event_type"),
]


class ResearchTrace(TraceModel):
    """A stable serialization of one recorder-observed event sequence."""

    schema_version: Literal["enterprise-research-trace/1.0.0"] = (
        "enterprise-research-trace/1.0.0"
    )
    trace_id: str = Field(
        min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$"
    )
    run_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    case_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    query_reference: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    execution_status: ResearchExecutionStatus
    ordering_basis: Literal["recorder_sequence"] = "recorder_sequence"
    events: tuple[TraceEvent, ...] = Field(min_length=1, max_length=MAX_TRACE_EVENTS)
    dropped_event_count: int = Field(default=0, ge=0)
    error: TraceErrorMetadata | None = None
    output_artifact_reference: str | None = None

    _validate_query_reference = field_validator("query_reference")(_validate_reference)
    _validate_output_reference = field_validator("output_artifact_reference")(
        _validate_reference
    )
    _validate_run_and_case_references = field_validator("run_id", "case_id")(
        lambda value: _validate_id(value, label="run_or_case_id", max_length=200)
    )
    _validate_trace_id = field_validator("trace_id")(
        lambda value: _validate_id(value, label="trace_id", max_length=100)
    )
    _validate_query_id = field_validator("query_reference")(
        lambda value: _validate_id(value, label="query_reference", max_length=500)
    )

    @field_validator("started_at", "completed_at")
    @classmethod
    def timezone_is_explicit(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("trace timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def lifecycle_is_consistent(self) -> "ResearchTrace":
        if not isinstance(self.events[0], ResearchStartedEvent):
            raise ValueError("the first trace event must be research_started")
        if sum(isinstance(event, ResearchStartedEvent) for event in self.events) != 1:
            raise ValueError("a trace must contain exactly one research_started event")
        if self.events[0].recorded_at != self.started_at:
            raise ValueError("research_started timestamp must match started_at")
        if tuple(event.sequence for event in self.events) != tuple(range(len(self.events))):
            raise ValueError("trace event sequence must be contiguous and ordered")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at")

        terminal_events = [
            event for event in self.events if isinstance(event, ResearchCompletedEvent)
        ]
        terminal = len(terminal_events) == 1 and terminal_events[0] is self.events[-1]
        if self.execution_status is ResearchExecutionStatus.RUNNING:
            if self.completed_at is not None or self.error is not None or terminal_events:
                raise ValueError("running traces cannot have terminal metadata")
        else:
            if self.completed_at is None or not terminal:
                raise ValueError("terminal traces require completion metadata and event")
            completion = self.events[-1]
            assert isinstance(completion, ResearchCompletedEvent)
            if completion.recorded_at != self.completed_at:
                raise ValueError("research_completed timestamp must match completed_at")
            if completion.output_artifact_reference != self.output_artifact_reference:
                raise ValueError("trace and completion artifact references differ")
            if completion.execution_status is not self.execution_status:
                raise ValueError("trace and completion event statuses differ")
            if self.execution_status is ResearchExecutionStatus.FAILED:
                if self.error is None or completion.error != self.error:
                    raise ValueError("failed traces require matching bounded errors")
            elif self.error is not None:
                raise ValueError("completed traces cannot contain an error")
        return self

    def to_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        ) + "\n"


_active_trace: ContextVar["ResearchTraceRecorder | None"] = ContextVar(
    "enterprise_trace", default=None
)
_claim_gate_trace_phase: ContextVar[ClaimGateTracePhase] = ContextVar(
    "claim_gate_trace_phase", default=ClaimGateTracePhase.PRE_GENERATION
)


def current_trace() -> "ResearchTraceRecorder | None":
    return _active_trace.get()


@contextmanager
def claim_gate_trace_phase(phase: ClaimGateTracePhase):
    token = _claim_gate_trace_phase.set(phase)
    try:
        yield
    finally:
        _claim_gate_trace_phase.reset(token)


class ResearchTraceRecorder:
    """In-memory recorder with opt-in local JSON export.

    Core callers use the ``try_*`` helpers so trace validation or filesystem
    failures cannot change a research decision. Strict methods remain available
    for tests and explicit integrations.
    """

    def __init__(
        self,
        run_id: str | None = None,
        *,
        trace_id: str | None = None,
        case_id: str | None = None,
        query_reference: str | None = None,
        max_events: int = MAX_TRACE_EVENTS,
        clock: Callable[[], datetime] | None = None,
        timer: Callable[[], float] | None = None,
    ):
        if max_events < 2 or max_events > MAX_TRACE_EVENTS:
            raise ValueError(f"max_events must be between 2 and {MAX_TRACE_EVENTS}")
        self.trace_id = _validate_id(
            trace_id or f"trace_{uuid4().hex}",
            label="trace_id",
            max_length=100,
        )
        assert self.trace_id is not None
        self.run_id = (
            _sanitized_id(run_id, label="run_id") if run_id is not None else None
        )
        self.case_id = (
            _sanitized_id(case_id, label="case_id") if case_id is not None else None
        )
        self.query_reference = (
            _sanitized_id(
                query_reference, label="query_reference", max_length=500
            )
            if query_reference is not None
            else None
        )
        self.max_events = max_events
        self._operational_max_events = max_events
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._timer = timer or time.perf_counter
        self._started_timer = self._timer()
        self.started_at = self._clock()
        self.completed_at: datetime | None = None
        self.execution_status = ResearchExecutionStatus.RUNNING
        self.error: TraceErrorMetadata | None = None
        self.output_artifact_reference: str | None = None
        self._events: list[TraceEvent] = []
        self._dropped_trace_events = 0
        self.dropped_events = 0
        self.search_calls = 0
        self.search_failures = 0
        self.retrieval_calls = 0
        self.selected_evidence_count = 0
        self._operational_events: list[dict] = []
        self.last_record_error_type: str | None = None
        self.last_export_error_type: str | None = None
        self._pending_policy: dict | None = None
        self._events.append(
            ResearchStartedEvent(sequence=0, recorded_at=self.started_at)
        )

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    @property
    def trace_events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    @property
    def operational_events(self) -> tuple[dict, ...]:
        return tuple(self._operational_events)

    def append(self, event: TraceEvent) -> None:
        if self.execution_status is not ResearchExecutionStatus.RUNNING:
            raise RuntimeError("cannot append to a completed trace")
        if event.sequence != len(self._events):
            raise ValueError("event sequence must match recorder append order")
        if len(self._events) >= self.max_events - 1:
            self._dropped_trace_events += 1
            return
        self._events.append(event)

    def _append_new(self, event_type, **values) -> None:
        self.append(
            event_type(
                sequence=len(self._events), recorded_at=self._clock(), **values
            )
        )

    def _attempt(self, callback: Callable[[], None]) -> bool:
        try:
            callback()
            return True
        except Exception as exc:  # Trace side effects are non-authoritative.
            self.last_record_error_type = type(exc).__name__
            return False

    def _read_timer(self) -> float | None:
        try:
            value = self._timer()
            return value if math.isfinite(value) else None
        except Exception as exc:
            self.last_record_error_type = type(exc).__name__
            return None

    @contextmanager
    def activate(self):
        token = _active_trace.set(self)
        try:
            yield self
        finally:
            _active_trace.reset(token)

    @contextmanager
    def stage(self, name: str):
        """Compatibility timing; these are not typed architecture events."""

        if name not in {"research", "report", "search", "retrieval"}:
            raise ValueError("Unknown trace stage")
        started = self._read_timer()
        event = {"stage": name, "status": "completed"}
        try:
            yield
        except BaseException as exc:
            event.update(status="failed", error_type=type(exc).__name__)
            if name == "search":
                self.search_failures += 1
            raise
        finally:
            ended = self._read_timer()
            duration = (
                ended - started
                if ended is not None and started is not None and ended >= started
                else None
            )
            event["duration_s"] = duration
            self._append_operational(event)

    def _append_operational(self, event: dict) -> None:
        if len(self._operational_events) < self._operational_max_events:
            self._operational_events.append(event)
        else:
            self.dropped_events += 1

    def task_policy(self, classification, policy, limitations, authority_weight):
        """Retain bounded policy metadata until selection is observed."""

        self._pending_policy = {
            "stage": "task_policy",
            "task_category": classification.category.value,
            "classifier_version": classification.classifier_version,
            "classifier_confidence": classification.confidence,
            "fallback_used": classification.fallback_used,
            "policy_version": policy.policy_version,
            "authority_weight": authority_weight,
            "policy_authority_weight_anchor": policy.authority_weight,
            "authority_weight_fallback_used": classification.fallback_used,
            "freshness_mode": policy.freshness_mode.value,
            "max_age_days": policy.max_age_days,
            "preferred_source_types": list(policy.preferred_source_types),
            "corroboration_rule": policy.corroboration_rule,
            "primary_source_rule": policy.primary_source_rule,
            "independent_source_rule": policy.independent_source_rule,
            "policy_reason_codes": list(policy.reason_codes),
            "policy_limitation_codes": list(limitations),
        }
        self._append_operational(dict(self._pending_policy))

    def try_record_task_policy(
        self, classification, policy, limitations, authority_weight
    ) -> bool:
        return self._attempt(
            lambda: self.task_policy(
                classification, policy, limitations, authority_weight
            )
        )

    def record_evidence_selection(
        self,
        result,
        *,
        authority_weight: float | None,
        similarity_threshold: float | None,
        task_category: str | None = None,
        candidate_evidence_count: int | None = None,
    ) -> None:
        diagnostics = tuple(result.retrieval_diagnostics[:MAX_EVENT_IDS])
        selected_ids = tuple(
            _sanitized_id(evidence.evidence_id, label="evidence_id")
            for evidence in result.evidences[:MAX_EVENT_IDS]
        )
        self.retrieval_calls += 1
        self.selected_evidence_count += len(result.evidences)
        self._append_new(
            EvidenceSelectionEvent,
            task_category=task_category,
            candidate_evidence_count=candidate_evidence_count,
            selected_evidence_count=len(result.evidences),
            authority_weight=authority_weight,
            similarity_threshold=similarity_threshold,
            selected_evidence_ids=selected_ids,
            scorer_summary=tuple(
                RetrievalScoreTrace(
                    evidence_id=_sanitized_id(
                        item.evidence_id, label="evidence_id"
                    ),
                    similarity_score=item.similarity_score,
                    authority_score=item.authority_score,
                    final_score=item.final_score,
                )
                for item in diagnostics
            ),
        )

    def retrieval(
        self,
        result,
        weight: float,
        similarity_threshold: float,
        task_classification=None,
        evidence_policy=None,
        policy_limitations=(),
        candidate_evidence_count: int | None = None,
    ):
        """Compatibility hook used by the existing ContextManager."""

        category = (
            task_classification.category.value
            if task_classification is not None
            else None
        )
        self._attempt(
            lambda: self.record_evidence_selection(
                result,
                authority_weight=weight,
                similarity_threshold=similarity_threshold,
                task_category=category,
                candidate_evidence_count=candidate_evidence_count,
            )
        )
        event = {
            "stage": "retrieval_selection",
            "source_reliability_weight": weight,
            "similarity_threshold": similarity_threshold,
            "selected_count": len(result.evidences),
            "scores": [
                {
                    **item.model_dump(exclude={"evidence_id"}),
                    "evidence_id": _sanitized_id(
                        item.evidence_id, label="evidence_id"
                    ),
                }
                for item in result.retrieval_diagnostics
            ],
        }
        if task_classification is not None and evidence_policy is not None:
            event.update(
                task_category=task_classification.category.value,
                classifier_version=task_classification.classifier_version,
                classifier_confidence=task_classification.confidence,
                fallback_used=task_classification.fallback_used,
                policy_version=evidence_policy.policy_version,
                authority_weight=weight,
                policy_authority_weight_anchor=evidence_policy.authority_weight,
                authority_weight_fallback_used=task_classification.fallback_used,
                freshness_mode=evidence_policy.freshness_mode.value,
                max_age_days=evidence_policy.max_age_days,
                preferred_source_types=list(evidence_policy.preferred_source_types),
                corroboration_rule=evidence_policy.corroboration_rule,
                primary_source_rule=evidence_policy.primary_source_rule,
                independent_source_rule=evidence_policy.independent_source_rule,
                policy_reason_codes=list(evidence_policy.reason_codes),
                policy_limitation_codes=list(policy_limitations),
            )
        self._append_operational(event)

    def record_claim_gate(self, claim: Claim, result: ClaimGateResult) -> None:
        if claim.claim_id != result.claim_id:
            raise ValueError("claim and ClaimGateResult IDs must match")
        obligations = result.resolved_obligations
        if obligations is None:
            raise ValueError("ClaimGateResult must contain resolved obligations")
        self._append_new(
            ClaimGateEvent,
            claim_id=_sanitized_id(claim.claim_id, label="claim_id"),
            phase=_claim_gate_trace_phase.get(),
            risk_types=tuple(item.value for item in claim.risk_types),
            is_material=claim.is_material,
            evidence_strength_rules=tuple(
                item.value for item in obligations.evidence_strength_rules
            ),
            required_entity_ids=tuple(
                _sanitized_id(value, label="required_entity_id")
                for value in obligations.required_entity_ids
            ),
            required_material_side_ids=tuple(
                _sanitized_id(value, label="required_material_side_id")
                for value in obligations.required_material_side_ids
            ),
            requires_independent_adjudicator=obligations.requires_independent_adjudicator,
            gate_decision=result.decision.value,
        )

    def try_record_claim_gate(self, claim: Claim, result: ClaimGateResult) -> bool:
        return self._attempt(lambda: self.record_claim_gate(claim, result))

    def record_generation(
        self,
        records: Iterable[GeneratedClaimRecord] | None = None,
        *,
        output_artifact_reference: str | None = None,
    ) -> None:
        materialized = list(records) if records is not None else None
        ids = (
            tuple(
                _sanitized_id(record.claim_id, label="claim_id")
                for record in materialized[:MAX_EVENT_IDS]
            )
            if materialized is not None
            else ()
        )
        self._append_new(
            GenerationEvent,
            generated_claim_count=(len(materialized) if materialized is not None else None),
            generated_claim_ids=ids,
            output_artifact_reference=_sanitized_reference(
                output_artifact_reference
            ),
        )

    def try_record_generation(self, *args, **kwargs) -> bool:
        return self._attempt(lambda: self.record_generation(*args, **kwargs))

    def record_grounding_validation(
        self,
        result: GroundingValidationResult,
        records: Iterable[GeneratedClaimRecord],
        *,
        repair_plan: GroundingRepairPlan | None = None,
    ) -> None:
        records_by_id = {record.claim_id: record for record in records}
        claim_ids = sorted(
            set(records_by_id)
            | {finding.claim_id for finding in result.findings}
            | set(result.validated_claim_ids)
            | set(result.repairable_claim_ids)
            | set(result.failed_claim_ids)
        )
        actions_by_claim: dict[str, list[str]] = {}
        if repair_plan is not None:
            for action in repair_plan.actions:
                actions_by_claim.setdefault(action.claim_id, []).append(
                    action.operation.value
                )
        for claim_id in claim_ids:
            finding_codes = tuple(
                dict.fromkeys(
                    finding.code.value
                    for finding in result.findings
                    if finding.claim_id == claim_id
                )
            )
            record = records_by_id.get(claim_id)
            self._append_new(
                GroundingValidationEvent,
                claim_id=_sanitized_id(claim_id, label="claim_id"),
                grounding_status=result.status.value,
                finding_codes=finding_codes,
                cited_evidence_count=(len(record.cited_evidence_ids) if record else 0),
                repair_required=claim_id in result.repairable_claim_ids,
                failed=claim_id in result.failed_claim_ids,
                planned_repair_action_types=tuple(
                    dict.fromkeys(actions_by_claim.get(claim_id, ()))
                ),
            )

    def try_record_grounding_validation(self, *args, **kwargs) -> bool:
        return self._attempt(lambda: self.record_grounding_validation(*args, **kwargs))

    def record_repair(self, plan: GroundingRepairPlan) -> None:
        for action in plan.actions:
            self._append_new(
                RepairEvent,
                claim_id=_sanitized_id(action.claim_id, label="claim_id"),
                action_type=action.operation.value,
                evidence_id=(
                    _sanitized_id(action.evidence_id, label="evidence_id")
                    if action.evidence_id is not None
                    else None
                ),
            )

    def try_record_repair(self, plan: GroundingRepairPlan) -> bool:
        return self._attempt(lambda: self.record_repair(plan))

    def complete(
        self,
        *,
        final_claim_count: int | None = None,
        output_artifact_reference: str | None = None,
    ) -> ResearchTrace:
        return self._finish(
            ResearchExecutionStatus.COMPLETED,
            final_claim_count=final_claim_count,
            output_artifact_reference=_sanitized_reference(
                output_artifact_reference
            ),
        )

    def fail(
        self,
        error: BaseException | TraceErrorMetadata,
        *,
        error_code: str | None = None,
        output_artifact_reference: str | None = None,
    ) -> ResearchTrace:
        metadata = (
            error
            if isinstance(error, TraceErrorMetadata)
            else TraceErrorMetadata(
                error_type=type(error).__name__,
                error_code=(
                    _sanitized_id(
                        error_code, label="error_code", max_length=64
                    )
                    if error_code is not None
                    else None
                ),
            )
        )
        return self._finish(
            ResearchExecutionStatus.FAILED,
            error=metadata,
            output_artifact_reference=_sanitized_reference(
                output_artifact_reference
            ),
        )

    def _finish(
        self,
        status: ResearchExecutionStatus,
        *,
        final_claim_count: int | None = None,
        error: TraceErrorMetadata | None = None,
        output_artifact_reference: str | None = None,
    ) -> ResearchTrace:
        if self.execution_status is not ResearchExecutionStatus.RUNNING:
            raise RuntimeError("trace is already complete")
        completed_at = self._clock()
        ended = self._read_timer()
        duration_value = (
            ended - self._started_timer
            if ended is not None and ended >= self._started_timer
            else None
        )
        completion = ResearchCompletedEvent(
            sequence=len(self._events),
            recorded_at=completed_at,
            execution_status=status,
            total_duration_seconds=duration_value,
            final_claim_count=final_claim_count,
            output_artifact_reference=output_artifact_reference,
            error=error,
        )
        self._events.append(completion)
        self.completed_at = completed_at
        self.execution_status = status
        self.error = error
        self.output_artifact_reference = output_artifact_reference
        return self.trace()

    def try_complete(self, **kwargs) -> ResearchTrace | None:
        try:
            return self.complete(**kwargs)
        except Exception as exc:
            self.last_record_error_type = type(exc).__name__
            return None

    def try_fail(self, error: BaseException, **kwargs) -> ResearchTrace | None:
        try:
            return self.fail(error, **kwargs)
        except Exception as exc:
            self.last_record_error_type = type(exc).__name__
            return None

    def trace(self) -> ResearchTrace:
        return ResearchTrace(
            trace_id=self.trace_id,
            run_id=self.run_id,
            case_id=self.case_id,
            query_reference=self.query_reference,
            started_at=self.started_at,
            completed_at=self.completed_at,
            execution_status=self.execution_status,
            events=tuple(self._events),
            dropped_event_count=self._dropped_trace_events,
            error=self.error,
            output_artifact_reference=self.output_artifact_reference,
        )

    def export(self, directory: Path | str = DEFAULT_TRACE_DIRECTORY) -> Path:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / f"{self.trace_id}.json"
        if path.exists():
            raise FileExistsError(f"trace artifact already exists: {path}")
        path.write_text(self.trace().to_json(), encoding="utf-8")
        return path

    def try_export(self, directory: Path | str = DEFAULT_TRACE_DIRECTORY) -> Path | None:
        try:
            return self.export(directory)
        except Exception as exc:
            self.last_export_error_type = type(exc).__name__
            return None

    def try_snapshot(self) -> dict | None:
        try:
            return self.snapshot()
        except Exception as exc:
            self.last_record_error_type = type(exc).__name__
            return None

    def snapshot(self) -> dict:
        """Backward-compatible operational view plus the typed trace snapshot."""

        ended = self._read_timer()
        elapsed = (
            ended - self._started_timer
            if ended is not None and ended >= self._started_timer
            else None
        )
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "elapsed_s": elapsed,
            "search_calls": self.search_calls,
            "search_failures": self.search_failures,
            "search_count_scope": (
                "ResearchConductor web searches; planning/MCP/provider internal retries excluded"
            ),
            "retrieval_calls": self.retrieval_calls,
            "selected_evidence_count": self.selected_evidence_count,
            "dropped_events": self.dropped_events,
            "events": list(self._operational_events),
            "research_trace": self.trace().model_dump(mode="json"),
        }


class RunTrace(ResearchTraceRecorder):
    """Compatibility facade for existing operational-diagnostics callers."""

    def __init__(
        self,
        run_id: str | None = None,
        max_events: int = MAX_TRACE_EVENTS,
        **kwargs,
    ):
        if max_events < 1 or max_events > MAX_TRACE_EVENTS:
            raise ValueError(f"max_events must be between 1 and {MAX_TRACE_EVENTS}")
        super().__init__(run_id, max_events=max(2, max_events), **kwargs)
        self._operational_max_events = max_events

    @property
    def events(self) -> tuple[dict, ...]:
        return self.operational_events


__all__ = [
    "ClaimGateEvent",
    "ClaimGateTracePhase",
    "DEFAULT_TRACE_DIRECTORY",
    "EvidenceSelectionEvent",
    "GenerationEvent",
    "GroundingValidationEvent",
    "RepairEvent",
    "ResearchCompletedEvent",
    "ResearchExecutionStatus",
    "ResearchStartedEvent",
    "ResearchTrace",
    "ResearchTraceEventType",
    "ResearchTraceRecorder",
    "RetrievalScoreTrace",
    "RunTrace",
    "TraceErrorMetadata",
    "claim_gate_trace_phase",
    "current_trace",
]
