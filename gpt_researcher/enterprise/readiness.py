"""Deterministic minimum-evidence readiness for one bounded retrieval retry."""

from __future__ import annotations

from enum import Enum
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict

from gpt_researcher.evidence.models import (
    Evidence,
    MetadataProvenanceKind,
)

from .requirements import (
    PlannedSubQuery,
    RequirementType,
    ResearchPlan,
    ResearchRequirement,
    canonical_label,
)
from .task_policy import ResearchTaskCategory


DEFAULT_SECOND_RETRIEVAL_QUERY_BUDGET = 5


class RequirementAnswerReadinessStatus(str, Enum):
    READY = "READY"
    NEEDS_RETRIEVAL = "NEEDS_RETRIEVAL"


class RequirementAnswerReadinessReason(str, Enum):
    NO_SUPPORTING_EVIDENCE = "NO_SUPPORTING_EVIDENCE"
    MISSING_COMPARISON_SIDE = "MISSING_COMPARISON_SIDE"
    NO_VERIFIABLE_TIME_CONTEXT = "NO_VERIFIABLE_TIME_CONTEXT"
    DEPENDENCY_NOT_READY = "DEPENDENCY_NOT_READY"
    READY = "READY"


class RequirementAnswerReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str
    status: RequirementAnswerReadinessStatus
    missing_target_entities: tuple[str, ...] = ()
    reason: RequirementAnswerReadinessReason


class SecondRetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str
    query: str


class SecondRetrievalDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    triggered: bool = False
    queries_count: int = 0
    requirement_ids: tuple[str, ...] = ()
    missing_target_entities: tuple[str, ...] = ()
    readiness_before: tuple[RequirementAnswerReadiness, ...] = ()
    readiness_after: tuple[RequirementAnswerReadiness, ...] = ()
    retrieval_budget_exhausted: tuple[str, ...] = ()
    additional_search_latency_s: float = 0.0
    additional_retrieved_candidates: int = 0


_TEMPORAL_MARKERS = (
    "latest",
    "current",
    "currently",
    "recent",
    "trend",
    "as of",
    "当前",
    "最新",
    "近期",
    "趋势",
)


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _contains_label(text: str, label: str) -> bool:
    normalized_text = _normalized_text(text)
    normalized_label = _normalized_text(label)
    if not normalized_label:
        return False
    if normalized_label.isascii() and all(
        char.isalnum() or char.isspace() or char in "_-" for char in normalized_label
    ):
        return re.search(
            rf"(?<![\w]){re.escape(normalized_label)}(?![\w])", normalized_text
        ) is not None
    return normalized_label in normalized_text


def canonical_url(value: str) -> str:
    """Return a conservative page identity without fragments/default ports."""

    try:
        parsed = urlsplit(value.strip())
        scheme = parsed.scheme.casefold()
        hostname = (parsed.hostname or "").casefold()
        if not scheme or not hostname:
            return value.strip()
        port = parsed.port
        if port is not None and not (
            (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        ):
            hostname = f"{hostname}:{port}"
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        return urlunsplit((scheme, hostname, path, parsed.query, ""))
    except ValueError:
        return value.strip()


def _is_traceable(evidence: Evidence) -> bool:
    return bool(evidence.url.strip() and evidence.content.strip())


def _has_verifiable_time_context(evidence: Evidence) -> bool:
    provenance = evidence.metadata_provenance
    return bool(
        evidence.publication_date
        and provenance.publication_date is not MetadataProvenanceKind.UNKNOWN
    ) or bool(
        evidence.updated_date
        and provenance.updated_date is not MetadataProvenanceKind.UNKNOWN
    )


def _is_temporal_requirement(requirement: ResearchRequirement) -> bool:
    # The task category describes the request as a whole; it must not turn every
    # requirement in a mixed trend task into a freshness-sensitive requirement.
    explicit_context = " ".join(
        (
            requirement.text,
            *requirement.source_dimensions,
            *requirement.constraints,
        )
    )
    normalized = _normalized_text(explicit_context)
    return any(_contains_label(normalized, marker) for marker in _TEMPORAL_MARKERS)


def _structured_scope(requirement: ResearchRequirement) -> tuple[str, ...]:
    return (
        *requirement.source_dimensions,
        *requirement.constraints,
        *requirement.target_entities,
    )


def _matches_distinguishing_scope(
    requirement: ResearchRequirement,
    peers: tuple[ResearchRequirement, ...],
    evidence: Evidence,
) -> bool:
    """Match an explicit scope anchor that is absent from every mapped peer."""

    peer_scopes = [
        {canonical_label(value) for value in _structured_scope(peer)}
        for peer in peers
        if peer.requirement_id != requirement.requirement_id
    ]
    distinguishing_anchors = (
        anchor
        for anchor in _structured_scope(requirement)
        if all(canonical_label(anchor) not in scope for scope in peer_scopes)
    )
    evidence_text = f"{evidence.title}\n{evidence.content}"
    return any(_contains_label(evidence_text, anchor) for anchor in distinguishing_anchors)


def _evidence_by_requirement(
    plan: ResearchPlan,
    evidences: list[Evidence],
) -> dict[str, list[Evidence]]:
    sub_queries_by_query: dict[str, list[PlannedSubQuery]] = {}
    for sub_query in plan.sub_queries:
        sub_queries_by_query.setdefault(canonical_label(sub_query.query), []).append(
            sub_query
        )
    requirements_by_id = {
        item.requirement_id: item for item in plan.requirements
    }
    result: dict[str, list[Evidence]] = {
        item.requirement_id: [] for item in plan.requirements
    }
    for evidence in evidences:
        if not _is_traceable(evidence):
            continue
        assigned_requirement_ids: set[str] = set()
        for sub_query in sub_queries_by_query.get(
            canonical_label(evidence.sub_query), ()
        ):
            mapped_requirements = tuple(
                requirements_by_id[requirement_id]
                for requirement_id in sub_query.requirement_ids
                if requirement_id in requirements_by_id
            )
            if len(mapped_requirements) == 1:
                assigned_requirement_ids.add(mapped_requirements[0].requirement_id)
                continue
            for requirement in mapped_requirements:
                if _matches_distinguishing_scope(
                    requirement, mapped_requirements, evidence
                ):
                    assigned_requirement_ids.add(requirement.requirement_id)
        for requirement_id in assigned_requirement_ids:
            result[requirement_id].append(evidence)
    return result


def _covered_entities(
    requirement: ResearchRequirement,
    evidences: list[Evidence],
) -> set[str]:
    covered = set()
    for target in requirement.target_entities:
        if any(
            _contains_label(f"{evidence.title}\n{evidence.content}", target)
            for evidence in evidences
        ):
            covered.add(canonical_label(target))
    return covered


def evaluate_requirement_readiness(
    plan: ResearchPlan,
    evidences: list[Evidence],
    *,
    task_category: ResearchTaskCategory | None = None,
) -> tuple[RequirementAnswerReadiness, ...]:
    """Apply only minimum-answer rules; Claim Gate obligations are irrelevant."""

    evidence_map = _evidence_by_requirement(plan, evidences)
    preliminary: dict[str, RequirementAnswerReadiness] = {}
    for requirement in plan.requirements:
        supporting = evidence_map[requirement.requirement_id]
        if requirement.requirement_type is RequirementType.RECOMMENDATION:
            continue

        treats_entities_as_sides = (
            requirement.requirement_type is RequirementType.COMPARATIVE
            or (
                task_category
                is ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION
                and len(requirement.target_entities) >= 2
            )
        )
        if treats_entities_as_sides:
            covered = _covered_entities(requirement, supporting)
            missing = tuple(
                target
                for target in requirement.target_entities
                if canonical_label(target) not in covered
            )
            if missing:
                preliminary[requirement.requirement_id] = RequirementAnswerReadiness(
                    requirement_id=requirement.requirement_id,
                    status=RequirementAnswerReadinessStatus.NEEDS_RETRIEVAL,
                    missing_target_entities=missing,
                    reason=(
                        RequirementAnswerReadinessReason.NO_SUPPORTING_EVIDENCE
                        if len(missing) == len(requirement.target_entities)
                        else RequirementAnswerReadinessReason.MISSING_COMPARISON_SIDE
                    ),
                )
                continue
        elif not supporting:
            preliminary[requirement.requirement_id] = RequirementAnswerReadiness(
                requirement_id=requirement.requirement_id,
                status=RequirementAnswerReadinessStatus.NEEDS_RETRIEVAL,
                reason=RequirementAnswerReadinessReason.NO_SUPPORTING_EVIDENCE,
            )
            continue

        if _is_temporal_requirement(requirement) and not any(
            _has_verifiable_time_context(item) for item in supporting
        ):
            preliminary[requirement.requirement_id] = RequirementAnswerReadiness(
                requirement_id=requirement.requirement_id,
                status=RequirementAnswerReadinessStatus.NEEDS_RETRIEVAL,
                reason=RequirementAnswerReadinessReason.NO_VERIFIABLE_TIME_CONTEXT,
            )
            continue

        preliminary[requirement.requirement_id] = RequirementAnswerReadiness(
            requirement_id=requirement.requirement_id,
            status=RequirementAnswerReadinessStatus.READY,
            reason=RequirementAnswerReadinessReason.READY,
        )

    dependencies = tuple(
        item
        for item in plan.requirements
        if item.requirement_type in (RequirementType.FACTUAL, RequirementType.COMPARATIVE)
    )
    results = []
    for requirement in plan.requirements:
        if requirement.requirement_type is RequirementType.RECOMMENDATION:
            ready = all(
                preliminary[item.requirement_id].status
                is RequirementAnswerReadinessStatus.READY
                for item in dependencies
            )
            results.append(RequirementAnswerReadiness(
                requirement_id=requirement.requirement_id,
                status=(RequirementAnswerReadinessStatus.READY if ready
                        else RequirementAnswerReadinessStatus.NEEDS_RETRIEVAL),
                reason=(RequirementAnswerReadinessReason.READY if ready
                        else RequirementAnswerReadinessReason.DEPENDENCY_NOT_READY),
            ))
        else:
            results.append(preliminary[requirement.requirement_id])
    return tuple(results)


def _comparison_detail(requirement: ResearchRequirement) -> str:
    structured = " ".join((*requirement.source_dimensions, *requirement.constraints))
    if structured.strip():
        return " ".join(structured.split())
    detail = requirement.text
    for target in requirement.target_entities:
        detail = re.sub(re.escape(target), " ", detail, flags=re.IGNORECASE)
    detail = re.sub(
        r"\b(compare|comparison|versus|vs\.?|and)\b|比较|对比|与|和",
        " ",
        detail,
        flags=re.IGNORECASE,
    )
    return " ".join(detail.split())


def build_second_retrieval_queries(
    plan: ResearchPlan,
    readiness: tuple[RequirementAnswerReadiness, ...],
    *,
    budget: int = DEFAULT_SECOND_RETRIEVAL_QUERY_BUDGET,
) -> tuple[tuple[SecondRetrievalQuery, ...], tuple[str, ...]]:
    """Build at most one deterministic query per unmet non-recommendation item."""

    requirements = {item.requirement_id: item for item in plan.requirements}
    queries = []
    exhausted = []
    for item in readiness:
        requirement = requirements[item.requirement_id]
        if (
            item.status is RequirementAnswerReadinessStatus.READY
            or requirement.requirement_type is RequirementType.RECOMMENDATION
        ):
            continue
        if len(queries) >= budget:
            exhausted.append(item.requirement_id)
            continue
        if (
            item.missing_target_entities
            and len(item.missing_target_entities) < len(requirement.target_entities)
        ):
            query = " ".join(
                (
                    " ".join(item.missing_target_entities),
                    _comparison_detail(requirement),
                )
            ).strip()
        else:
            query = requirement.text
        queries.append(SecondRetrievalQuery(
            requirement_id=item.requirement_id,
            query=" ".join(query.split()),
        ))
    return tuple(queries), tuple(exhausted)


def extend_plan_with_second_queries(
    plan: ResearchPlan,
    queries: tuple[SecondRetrievalQuery, ...],
) -> ResearchPlan:
    additions = tuple(
        PlannedSubQuery(query=item.query, requirement_ids=(item.requirement_id,))
        for item in queries
    )
    return plan.model_copy(update={"sub_queries": plan.sub_queries + additions})
