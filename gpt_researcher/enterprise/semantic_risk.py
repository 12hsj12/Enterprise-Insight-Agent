"""Semantic-only routing for final-render evidence audit units.

The router decides whether a complete, stable Writer unit needs the existing
strict Evidence Reliability path.  It does not decide truth, evidence support,
qualification, Claim Gate, Grounding, or rendered wording.
"""

from __future__ import annotations

from enum import Enum
import json
from typing import Awaitable, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .unit_audit import AuditUnitType, WriterAuditUnit


class SemanticRiskCategory(str, Enum):
    OBJECTIVE_CAPABILITY = "OBJECTIVE_CAPABILITY"
    AVAILABILITY_STATUS = "AVAILABILITY_STATUS"
    TEMPORAL_RELEASE = "TEMPORAL_RELEASE"
    COMPANY_ACTION = "COMPANY_ACTION"
    NUMERIC_DATE_PRICE_SLA = "NUMERIC_DATE_PRICE_SLA"
    BENCHMARK_PERFORMANCE = "BENCHMARK_PERFORMANCE"
    COMPARATIVE_SUPERLATIVE = "COMPARATIVE_SUPERLATIVE"
    MARKET_RANK_SHARE = "MARKET_RANK_SHARE"
    STRONG_CAUSAL = "STRONG_CAUSAL"
    ORDINARY_CONTEXT = "ORDINARY_CONTEXT"
    ANALYSIS_RECOMMENDATION = "ANALYSIS_RECOMMENDATION"
    STRUCTURAL_NONCLAIM = "STRUCTURAL_NONCLAIM"


SEMANTIC_HIGH_RISK_CATEGORIES = frozenset({
    SemanticRiskCategory.OBJECTIVE_CAPABILITY,
    SemanticRiskCategory.AVAILABILITY_STATUS,
    SemanticRiskCategory.TEMPORAL_RELEASE,
    SemanticRiskCategory.COMPANY_ACTION,
    SemanticRiskCategory.NUMERIC_DATE_PRICE_SLA,
    SemanticRiskCategory.BENCHMARK_PERFORMANCE,
    SemanticRiskCategory.COMPARATIVE_SUPERLATIVE,
    SemanticRiskCategory.MARKET_RANK_SHARE,
    SemanticRiskCategory.STRONG_CAUSAL,
})


class SemanticRiskAssignment(BaseModel):
    """One semantic category for one stable unit; no truth judgment is stored."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str = Field(min_length=1, max_length=100)
    category: SemanticRiskCategory


class SemanticRiskRouting(BaseModel):
    """Validated routing plus explicit conservative-fallback accounting."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["complete", "partial_fallback", "fallback"]
    assignments: list[SemanticRiskAssignment] = Field(default_factory=list, max_length=4000)
    fallback_audit_unit_ids: list[str] = Field(default_factory=list, max_length=4000)
    unrouted_unit_ids: list[str] = Field(default_factory=list, max_length=4000)
    duplicate_unit_count: int = Field(default=0, ge=0)
    unknown_unit_count: int = Field(default=0, ge=0)
    invalid_route_count: int = Field(default=0, ge=0)
    provider_error_count: int = Field(default=0, ge=0)
    error_codes: list[str] = Field(default_factory=list, max_length=100)

    def category_by_unit(self) -> dict[str, SemanticRiskCategory]:
        return {item.unit_id: item.category for item in self.assignments}

    def semantic_high_risk_unit_ids(self) -> set[str]:
        return {
            item.unit_id for item in self.assignments
            if item.category in SEMANTIC_HIGH_RISK_CATEGORIES
        }

    def strict_audit_unit_ids(self) -> set[str]:
        return self.semantic_high_risk_unit_ids() | set(self.fallback_audit_unit_ids)


Completion = Callable[..., Awaitable[str]]
_ROUTER_CHUNK_SIZE = 60


def is_structural_unit(unit: WriterAuditUnit) -> bool:
    """Use Markdown structure, never vocabulary, for the structural boundary."""

    return unit.table_header or unit.unit_type is AuditUnitType.HEADING


def objective_candidate_unit_ids(units: list[WriterAuditUnit]) -> set[str]:
    """Every non-structural content unit is in the auditable denominator."""

    return {unit.unit_id for unit in units if not is_structural_unit(unit)}


def conservative_semantic_routing(
    units: list[WriterAuditUnit],
    *,
    error_code: str,
    provider_error_count: int = 0,
) -> SemanticRiskRouting:
    """Fail safe by auditing every content candidate as a complete unit."""

    structural = [
        SemanticRiskAssignment(
            unit_id=unit.unit_id,
            category=SemanticRiskCategory.STRUCTURAL_NONCLAIM,
        )
        for unit in units if is_structural_unit(unit)
    ]
    candidates = sorted(objective_candidate_unit_ids(units))
    return SemanticRiskRouting(
        status="fallback",
        assignments=structural,
        fallback_audit_unit_ids=candidates,
        unrouted_unit_ids=candidates,
        provider_error_count=provider_error_count,
        error_codes=[error_code],
    )


def validate_semantic_risk_response(
    raw_response: str,
    units: list[WriterAuditUnit],
) -> SemanticRiskRouting:
    """Validate total, unique unit coverage and fail conservatively per unit."""

    known = {unit.unit_id: unit for unit in units}
    try:
        raw = json.loads(raw_response)
    except Exception:
        return conservative_semantic_routing(units, error_code="MALFORMED_JSON")
    if (
        not isinstance(raw, dict)
        or set(raw) != {"routes"}
        or not isinstance(raw.get("routes"), list)
        or len(raw["routes"]) > 4000
    ):
        return conservative_semantic_routing(units, error_code="MALFORMED_SCHEMA")

    assignments: dict[str, SemanticRiskAssignment] = {}
    duplicate_ids: set[str] = set()
    unknown_count = 0
    invalid_count = 0
    for item in raw["routes"]:
        try:
            assignment = SemanticRiskAssignment.model_validate(item)
        except Exception:
            invalid_count += 1
            continue
        if assignment.unit_id not in known:
            unknown_count += 1
            continue
        if assignment.unit_id in assignments:
            duplicate_ids.add(assignment.unit_id)
            continue
        assignments[assignment.unit_id] = assignment
    for unit_id in duplicate_ids:
        assignments.pop(unit_id, None)

    missing = set(known) - set(assignments)
    invalid_structural = {
        unit_id for unit_id, assignment in assignments.items()
        if assignment.category is SemanticRiskCategory.STRUCTURAL_NONCLAIM
        and not is_structural_unit(known[unit_id])
    }
    # A content unit cannot self-exempt by being called structural.  It is
    # intentionally treated as an unrouted candidate and audited in full.
    for unit_id in invalid_structural:
        assignments.pop(unit_id, None)
    missing.update(invalid_structural)

    candidate_ids = objective_candidate_unit_ids(units)
    fallback_ids = sorted(missing & candidate_ids)
    unrouted = sorted(missing)
    errors = []
    if missing:
        errors.append("PARTIAL_OUTPUT")
    if duplicate_ids:
        errors.append("DUPLICATE_UNIT")
    if unknown_count:
        errors.append("UNKNOWN_UNIT")
    if invalid_count:
        errors.append("INVALID_ROUTE")
    if invalid_structural:
        errors.append("INVALID_STRUCTURAL_CLASSIFICATION")
    status: Literal["complete", "partial_fallback", "fallback"]
    if not errors:
        status = "complete"
    elif set(fallback_ids) == candidate_ids:
        status = "fallback"
    else:
        status = "partial_fallback"
    return SemanticRiskRouting(
        status=status,
        assignments=sorted(assignments.values(), key=lambda item: known[item.unit_id].ordinal),
        fallback_audit_unit_ids=fallback_ids,
        unrouted_unit_ids=unrouted,
        duplicate_unit_count=len(duplicate_ids),
        unknown_unit_count=unknown_count,
        invalid_route_count=invalid_count + len(invalid_structural),
        error_codes=errors,
    )


def _router_system_prompt() -> str:
    categories = ", ".join(category.value for category in SemanticRiskCategory)
    return (
        "You are a semantic risk router for an evidence-audited enterprise report. "
        "Classify every supplied stable Markdown unit exactly once. Return JSON only. "
        "You decide routing risk, never whether a statement is true, supported, cited, "
        "qualified, or well grounded. Do not rewrite, split, merge, omit, or repair text. "
        "Use meaning rather than literal trigger words. Objective claims about a product "
        "or service's ability, access, deployment, catalog, availability, status, release, "
        "company action, number, date, price, SLA, benchmark, performance, comparison, "
        "superlative, market position, or strong causation must receive the corresponding "
        "objective category even when phrased indirectly, with an omitted subject, in a "
        "continuation sentence, bullet, or table cell. A recommendation is "
        "ANALYSIS_RECOMMENDATION only when it adds no new objective factual proposition; "
        "otherwise route by the objective proposition. STRUCTURAL_NONCLAIM is only for "
        "headings or table headers with no factual proposition. Categories: "
        f"{categories}. The exact response shape is "
        "{\"routes\":[{\"unit_id\":\"...\",\"category\":\"...\"}]}"
    )


async def route_semantic_risk(
    researcher,
    units: list[WriterAuditUnit],
    *,
    completion: Completion | None = None,
) -> SemanticRiskRouting:
    """Classify all units in bounded calls; provider failures never bypass audit."""

    if not units:
        return SemanticRiskRouting(status="complete")
    if completion is None:
        from gpt_researcher.utils.llm import create_chat_completion
        completion = create_chat_completion

    all_assignments: list[SemanticRiskAssignment] = []
    fallback_ids: list[str] = []
    unrouted_ids: list[str] = []
    duplicate_count = unknown_count = invalid_count = provider_errors = 0
    error_codes: list[str] = []
    for start in range(0, len(units), _ROUTER_CHUNK_SIZE):
        chunk = units[start:start + _ROUTER_CHUNK_SIZE]
        try:
            response = await completion(
                model=researcher.cfg.smart_llm_model,
                llm_provider=researcher.cfg.smart_llm_provider,
                max_tokens=researcher.cfg.smart_token_limit,
                llm_kwargs=researcher.cfg.llm_kwargs,
                cost_callback=researcher.add_costs,
                messages=[
                    {"role": "system", "content": _router_system_prompt()},
                    {"role": "user", "content": json.dumps({
                        "units": [{
                            "unit_id": unit.unit_id,
                            "unit_type": unit.unit_type.value,
                            "text": unit.text,
                            "recommendation": unit.recommendation,
                            "table_header": unit.table_header,
                        } for unit in chunk],
                    })},
                ],
            )
            routed = validate_semantic_risk_response(response, chunk)
        except Exception:
            routed = conservative_semantic_routing(
                chunk, error_code="PROVIDER_ERROR", provider_error_count=1,
            )
        all_assignments.extend(routed.assignments)
        fallback_ids.extend(routed.fallback_audit_unit_ids)
        unrouted_ids.extend(routed.unrouted_unit_ids)
        duplicate_count += routed.duplicate_unit_count
        unknown_count += routed.unknown_unit_count
        invalid_count += routed.invalid_route_count
        provider_errors += routed.provider_error_count
        error_codes.extend(routed.error_codes)

    all_candidate_ids = objective_candidate_unit_ids(units)
    has_fallback = bool(fallback_ids or provider_errors or error_codes)
    status: Literal["complete", "partial_fallback", "fallback"]
    if not has_fallback:
        status = "complete"
    elif set(fallback_ids) == all_candidate_ids:
        status = "fallback"
    else:
        status = "partial_fallback"
    return SemanticRiskRouting(
        status=status,
        assignments=all_assignments,
        fallback_audit_unit_ids=list(dict.fromkeys(fallback_ids)),
        unrouted_unit_ids=list(dict.fromkeys(unrouted_ids)),
        duplicate_unit_count=duplicate_count,
        unknown_unit_count=unknown_count,
        invalid_route_count=invalid_count,
        provider_error_count=provider_errors,
        error_codes=list(dict.fromkeys(error_codes)),
    )
