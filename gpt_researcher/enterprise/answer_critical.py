"""Bounded semantic review of claims that materially affect the user's answer.

The reviewer selects locations; it never decides whether a claim is true or
supported.  Existing source qualification, ClaimGate, Grounding and cutoff
rules remain the only support decision path.
"""

from __future__ import annotations

from enum import Enum
import json
from typing import Awaitable, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .requirements import ResearchRequirement
from .unit_audit import AuditUnitType, WriterAuditUnit


class AnswerCriticalReason(str, Enum):
    REQUIREMENT_ANSWER = "REQUIREMENT_ANSWER"
    COMPARISON_DIFFERENTIATOR = "COMPARISON_DIFFERENTIATOR"
    PRODUCT_DECISION_FACT = "PRODUCT_DECISION_FACT"
    EXECUTIVE_DECISION = "EXECUTIVE_DECISION"
    RECOMMENDATION_PREMISE = "RECOMMENDATION_PREMISE"
    CONCLUSION_DECISION = "CONCLUSION_DECISION"
    NUMERIC_JUSTIFICATION = "NUMERIC_JUSTIFICATION"


class AnswerCriticalAssignment(BaseModel):
    """One factual Writer unit selected for the existing evidence audit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str = Field(min_length=1, max_length=100)
    reasons: tuple[AnswerCriticalReason, ...] = Field(min_length=1, max_length=7)
    requirement_ids: tuple[str, ...] = Field(default=(), max_length=60)


class RecommendationPremiseReview(BaseModel):
    """Location-only premise disclosure; recommendations are not gated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str = Field(min_length=1, max_length=100)
    premise_unit_ids: tuple[str, ...] = Field(default=(), max_length=60)
    has_inline_factual_premise: bool = False


class AnswerCriticalReview(BaseModel):
    """Validated critical locations and deterministic coverage diagnostics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["complete", "fallback"]
    assignments: tuple[AnswerCriticalAssignment, ...] = ()
    recommendations: tuple[RecommendationPremiseReview, ...] = ()
    fallback_audit_unit_ids: tuple[str, ...] = ()
    missing_requirement_ids: tuple[str, ...] = ()
    missing_recommendation_unit_ids: tuple[str, ...] = ()
    duplicate_unit_count: int = Field(default=0, ge=0)
    unknown_unit_count: int = Field(default=0, ge=0)
    invalid_review_count: int = Field(default=0, ge=0)
    provider_error_count: int = Field(default=0, ge=0)
    error_codes: tuple[str, ...] = ()

    def critical_unit_ids(self) -> set[str]:
        return {item.unit_id for item in self.assignments} | set(
            self.fallback_audit_unit_ids
        )

    def extraction_unit_ids(self) -> set[str]:
        return self.critical_unit_ids() | {
            item.unit_id for item in self.recommendations
        }

    def assignment_by_unit(self) -> dict[str, AnswerCriticalAssignment]:
        return {item.unit_id: item for item in self.assignments}

    def mapped_requirement_ids(self) -> set[str]:
        return {
            requirement_id
            for item in self.assignments
            for requirement_id in item.requirement_ids
        }


Completion = Callable[..., Awaitable[str]]


def _fallback_candidate_ids(units: list[WriterAuditUnit]) -> list[str]:
    """Bound failure scope to decision-bearing locations, not all prose."""

    return [
        unit.unit_id
        for unit in units
        if (
            unit.recommendation
            or (unit.unit_type is AuditUnitType.TABLE_CELL and not unit.table_header)
            or unit.claim_bearing
            or unit.high_risk
        )
    ]


def conservative_answer_critical_review(
    units: list[WriterAuditUnit],
    requirements: list[ResearchRequirement],
    *,
    error_code: str,
    provider_error_count: int = 0,
) -> AnswerCriticalReview:
    """Audit bounded decision locations when semantic review is unavailable."""

    candidates = _fallback_candidate_ids(units)
    requirement_ids = tuple(item.requirement_id for item in requirements)
    assignments = tuple(
        AnswerCriticalAssignment(
            unit_id=unit_id,
            reasons=(AnswerCriticalReason.REQUIREMENT_ANSWER,),
            requirement_ids=requirement_ids,
        )
        for unit_id in candidates
    )
    recommendations = tuple(
        RecommendationPremiseReview(
            unit_id=unit.unit_id,
            has_inline_factual_premise=unit.unit_id in candidates,
        )
        for unit in units if unit.recommendation
    )
    return AnswerCriticalReview(
        status="fallback",
        assignments=assignments,
        recommendations=recommendations,
        fallback_audit_unit_ids=tuple(candidates),
        provider_error_count=provider_error_count,
        error_codes=(error_code,),
    )


def validate_answer_critical_response(
    raw_response: str,
    units: list[WriterAuditUnit],
    requirements: list[ResearchRequirement],
) -> AnswerCriticalReview:
    """Validate location coverage without accepting support or truth judgments."""

    known_units = {unit.unit_id: unit for unit in units}
    known_requirements = {item.requirement_id for item in requirements}
    recommendation_ids = {unit.unit_id for unit in units if unit.recommendation}
    try:
        raw = json.loads(raw_response)
    except Exception:
        return conservative_answer_critical_review(
            units, requirements, error_code="MALFORMED_JSON",
        )
    if (
        not isinstance(raw, dict)
        or set(raw) != {"critical_units", "recommendations"}
        or not isinstance(raw.get("critical_units"), list)
        or not isinstance(raw.get("recommendations"), list)
    ):
        return conservative_answer_critical_review(
            units, requirements, error_code="MALFORMED_SCHEMA",
        )

    assignments: dict[str, AnswerCriticalAssignment] = {}
    recommendations: dict[str, RecommendationPremiseReview] = {}
    duplicates = unknown = invalid = 0
    for value in raw["critical_units"]:
        try:
            item = AnswerCriticalAssignment.model_validate(value)
        except Exception:
            invalid += 1
            continue
        if item.unit_id not in known_units or any(
            requirement_id not in known_requirements
            for requirement_id in item.requirement_ids
        ):
            unknown += 1
            continue
        if item.unit_id in assignments:
            duplicates += 1
            continue
        assignments[item.unit_id] = item

    for value in raw["recommendations"]:
        try:
            item = RecommendationPremiseReview.model_validate(value)
        except Exception:
            invalid += 1
            continue
        if (
            item.unit_id not in recommendation_ids
            or item.unit_id in item.premise_unit_ids
            or any(unit_id not in known_units for unit_id in item.premise_unit_ids)
            or any(unit_id in recommendation_ids for unit_id in item.premise_unit_ids)
        ):
            unknown += 1
            continue
        if item.unit_id in recommendations:
            duplicates += 1
            continue
        recommendations[item.unit_id] = item

    mapped = {
        requirement_id
        for item in assignments.values()
        for requirement_id in item.requirement_ids
    }
    missing_requirements = sorted(known_requirements - mapped)
    missing_recommendations = sorted(recommendation_ids - set(recommendations))
    if duplicates or unknown or invalid or missing_requirements or missing_recommendations:
        fallback = conservative_answer_critical_review(
            units, requirements, error_code="INCOMPLETE_OR_INVALID_REVIEW",
        )
        return fallback.model_copy(update={
            "missing_requirement_ids": tuple(missing_requirements),
            "missing_recommendation_unit_ids": tuple(missing_recommendations),
            "duplicate_unit_count": duplicates,
            "unknown_unit_count": unknown,
            "invalid_review_count": invalid,
        })

    return AnswerCriticalReview(
        status="complete",
        assignments=tuple(sorted(
            assignments.values(), key=lambda item: known_units[item.unit_id].ordinal,
        )),
        recommendations=tuple(sorted(
            recommendations.values(), key=lambda item: known_units[item.unit_id].ordinal,
        )),
    )


def _system_prompt() -> str:
    reasons = ", ".join(item.value for item in AnswerCriticalReason)
    return (
        "You review an already-written enterprise research answer and identify only "
        "answer-critical factual units. You select locations; you do not judge truth, "
        "support, confidence, source strength, or citation quality, and you do not rewrite "
        "text. A unit is answer-critical only when it directly answers a supplied frozen "
        "requirement; changes which compared product or vendor looks stronger; states a "
        "capability, availability, pricing, or current status used to distinguish options; "
        "is an executive-summary or final-conclusion decision statement; is a factual "
        "premise that changes a selection, migration, adoption, architecture, or operating "
        "recommendation; or is a numeric, benchmark, market, or SLA fact explicitly used "
        "to justify a conclusion. Ordinary background, transitions, generic explanations, "
        "and descriptive context are not critical by default. Include every differentiating "
        "comparison table data cell. Map every frozen requirement to at least one selected "
        "critical unit. List every supplied recommendation unit exactly once and expose its "
        "factual premise unit IDs; never use any recommendation unit as a premise. "
        "Set has_inline_factual_premise only when objective factual wording occurs inside "
        "that same recommendation unit. Return JSON only, with no extra fields. Reasons: "
        f"{reasons}. Shape: "
        '{"critical_units":[{"unit_id":"...","reasons":["REQUIREMENT_ANSWER"],'
        '"requirement_ids":["R1"]}],"recommendations":[{"unit_id":"...",'
        '"premise_unit_ids":["..."],"has_inline_factual_premise":false}]}'
    )


async def review_answer_critical_claims(
    researcher,
    units: list[WriterAuditUnit],
    requirements: list[ResearchRequirement],
    *,
    completion: Completion | None = None,
) -> AnswerCriticalReview:
    """Perform one bounded batched location review after the Writer draft."""

    if not units:
        return AnswerCriticalReview(status="complete")
    if completion is None:
        from gpt_researcher.utils.llm import create_chat_completion
        completion = create_chat_completion
    try:
        response = await completion(
            model=researcher.cfg.smart_llm_model,
            llm_provider=researcher.cfg.smart_llm_provider,
            max_tokens=researcher.cfg.smart_token_limit,
            llm_kwargs=researcher.cfg.llm_kwargs,
            cost_callback=researcher.add_costs,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": json.dumps({
                    "requirements": [item.model_dump(mode="json") for item in requirements],
                    "units": [unit.model_dump(mode="json") for unit in units],
                })},
            ],
        )
    except Exception:
        return conservative_answer_critical_review(
            units, requirements, error_code="PROVIDER_ERROR", provider_error_count=1,
        )
    return validate_answer_critical_response(response, units, requirements)
