"""Typed requirement planning produced by the existing research-planning call."""

from __future__ import annotations

import re
import unicodedata
import json
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def canonical_label(value: str) -> str:
    """Canonical identity for explicit dimensions and lightweight entity labels."""

    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


class RequirementType(str, Enum):
    FACTUAL = "FACTUAL"
    COMPARATIVE = "COMPARATIVE"
    RECOMMENDATION = "RECOMMENDATION"


class RequirementCoverageStatus(str, Enum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    NOT_COVERED = "NOT_COVERED"


class ResearchRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    requirement_id: str = Field(min_length=2, max_length=20)
    text: str = Field(min_length=1, max_length=3000)
    requirement_type: RequirementType
    order: int = Field(ge=1)
    constraints: tuple[str, ...] = ()
    target_entities: tuple[str, ...] = ()
    source_dimensions: tuple[str, ...] = ()

    @field_validator("requirement_id")
    @classmethod
    def valid_requirement_id(cls, value: str) -> str:
        if not re.fullmatch(r"R[1-9][0-9]*", value):
            raise ValueError("requirement_id must use R1, R2, ...")
        return value

    @field_validator("constraints", "target_entities", "source_dimensions")
    @classmethod
    def nonempty_unique_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(" ".join(value.split()) for value in values)
        if any(not value for value in normalized):
            raise ValueError("structured requirement values must not be empty")
        keys = [canonical_label(value) for value in normalized]
        if len(set(keys)) != len(keys):
            raise ValueError("structured requirement values must be unique")
        return normalized

    @model_validator(mode="after")
    def comparative_entities_are_explicit(self) -> "ResearchRequirement":
        if self.requirement_type is RequirementType.COMPARATIVE and len(self.target_entities) < 2:
            raise ValueError("comparative requirements need at least two target_entities")
        return self


class PlannedSubQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=1000)
    requirement_ids: tuple[str, ...] = Field(min_length=1)


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirements: tuple[ResearchRequirement, ...] = Field(min_length=1, max_length=60)
    sub_queries: tuple[PlannedSubQuery, ...] = Field(min_length=1, max_length=100)
    used_fallback: bool = False
    fallback_reason: str | None = None


class RequirementCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str
    status: RequirementCoverageStatus
    surviving_claim_ids: tuple[str, ...] = ()


def validate_research_plan(plan: ResearchPlan, explicit_dimensions: list[str]) -> ResearchPlan:
    """Validate structure without attempting natural-language interpretation."""

    if plan.used_fallback or plan.fallback_reason is not None:
        raise ValueError("provider output cannot declare local fallback state")
    requirements = sorted(plan.requirements, key=lambda item: item.order)
    ids = [item.requirement_id for item in requirements]
    if len(set(ids)) != len(ids):
        raise ValueError("requirement IDs must be unique")
    if [item.order for item in requirements] != list(range(1, len(requirements) + 1)):
        raise ValueError("requirement order must be contiguous from 1")

    texts = [canonical_label(item.text) for item in requirements]
    if len(set(texts)) != len(texts):
        raise ValueError("requirement text must not be an exact duplicate")

    dimension_keys = [
        (
            item.requirement_type,
            canonical_label(dimension),
            tuple(sorted(canonical_label(value) for value in item.target_entities)),
        )
        for item in requirements
        for dimension in item.source_dimensions
    ]
    if len(set(dimension_keys)) != len(dimension_keys):
        raise ValueError("duplicate requirement structure")

    known_ids = set(ids)
    for sub_query in plan.sub_queries:
        if any(requirement_id not in known_ids for requirement_id in sub_query.requirement_ids):
            raise ValueError("sub-query references an unknown requirement ID")

    covered_dimensions = {
        canonical_label(dimension)
        for requirement in requirements
        for dimension in requirement.source_dimensions
    }
    missing = [
        dimension for dimension in explicit_dimensions
        if canonical_label(dimension) not in covered_dimensions
    ]
    if missing:
        raise ValueError("explicit dimensions missing from structured requirements")
    return plan.model_copy(update={"requirements": tuple(requirements)})


def fallback_research_plan(
    *,
    target: str,
    topic: str,
    dimensions: list[str],
    cutoff_date: date | str | None,
    reason: str,
) -> ResearchPlan:
    """Keep the user's target in every fallback question and search query."""

    requirements: list[ResearchRequirement] = []
    target_entities = (target,) if target.strip() else ()
    comparison_body = re.sub(
        r"^(?:比较|对比)\s*|^compare\s+", "", target.strip(),
        flags=re.IGNORECASE,
    )
    comparison_parts = re.split(
        r"\s*(?:与|和|及|\band\b|\bversus\b|\bvs\.?\b)\s*",
        comparison_body, maxsplit=1, flags=re.IGNORECASE,
    )
    if len(comparison_parts) == 2:
        left = comparison_parts[0].strip(" ,.:;，。：；")
        right = re.split(r"(?:的|在|方面)|[,，。]", comparison_parts[1], maxsplit=1)[0]
        right = right.strip(" ,.:;，。：；")
        if left and right:
            target_entities = (left, right)
    generic_topic = canonical_label(topic) in {
        "development research", "competitive intelligence", "research"
    }

    def requirement_type(text: str) -> RequirementType:
        # Only the requested wording is inspected. A generic benchmark topic
        # must never turn a decision request into a factual requirement.
        if re.search(r"建议|选型|迁移|决策|recommend|choose|selection|decision",
                     text, flags=re.IGNORECASE):
            return RequirementType.RECOMMENDATION
        if (len(target_entities) >= 2
                and re.search(r"比较|对比|compare|comparison|versus|\bvs\.?\b",
                              text, flags=re.IGNORECASE)):
            return RequirementType.COMPARATIVE
        return RequirementType.FACTUAL

    for dimension in dimensions:
        requirements.append(ResearchRequirement(
            requirement_id=f"R{len(requirements) + 1}",
            text=f"{target}: {dimension}",
            requirement_type=requirement_type(dimension),
            order=len(requirements) + 1,
            target_entities=target_entities,
            source_dimensions=(dimension,),
        ))
    effective_topic = target if generic_topic else (topic or target)
    topic_key = canonical_label(effective_topic)
    dimension_keys = {canonical_label(dimension) for dimension in dimensions}
    if not requirements or topic_key not in dimension_keys:
        requirements.append(ResearchRequirement(
            requirement_id=f"R{len(requirements) + 1}",
            text=effective_topic,
            requirement_type=requirement_type(effective_topic),
            order=len(requirements) + 1,
            target_entities=target_entities,
        ))
    sub_queries = tuple(
        PlannedSubQuery(query=requirement.text, requirement_ids=(requirement.requirement_id,))
        for requirement in requirements
    )
    return ResearchPlan(
        requirements=tuple(requirements),
        sub_queries=sub_queries,
        used_fallback=True,
        fallback_reason=reason,
    )


def planning_prompt_suffix(
    *, target: str, topic: str, dimensions: list[str], cutoff_date: date | str | None,
) -> str:
    """Instructions appended to the existing planning prompt, not a new LLM call."""

    context = {
        "target": target,
        "topic": topic,
        "dimensions": dimensions,
        "cutoff_context": str(cutoff_date) if cutoff_date is not None else None,
    }
    schema = ResearchPlan.model_json_schema()
    return f"""

For this Enterprise Insight task, use the same response to plan BOTH report
requirements and search sub-queries. A requirement is an independent question
the user ultimately wants the report to answer. It is not a search keyword,
web topic, background fact, or an extra issue you think may be useful.

Rules:
- Preserve every explicitly requested dimension; split multi-dimensional
  comparisons into separate requirements and declare the matching value in
  source_dimensions.
- Make a recommendation a separate RECOMMENDATION requirement.
- Preserve user conditions in constraints and name comparison subjects in
  target_entities.
- Do not add research dimensions the user did not request.
- Return normally 1-5 requirements, but retain every item when the user
  explicitly requests more than five.
- These rules apply equally to Chinese and English input.
- dimensions are explicit research dimensions. They must appear in requirements
  without replacing other explicit tasks in topic.
- Use requirement IDs R1, R2, ... and contiguous order values 1, 2, ... .
- Every sub-query must reference one or more existing requirement IDs.

Structured task context: {json.dumps(context, ensure_ascii=False)}

Return ONLY JSON matching this schema (used_fallback must be false and
fallback_reason must be null):
{json.dumps(schema, ensure_ascii=False)}
"""
