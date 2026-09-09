from __future__ import annotations

import hashlib
import unicodedata
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClaimRiskType(str, Enum):
    """Frozen V2 high-risk factual-claim taxonomy."""

    NUMERIC_VALUE = "numeric_value"
    DATE_OR_TIME_WINDOW = "date_or_time_window"
    RELEASE_STATUS_AVAILABILITY = "release_status_availability"
    COMPARATIVE_CLAIM = "comparative_claim"
    SUPERLATIVE_OR_RANKING = "superlative_or_ranking"
    MARKET_METRIC = "market_metric"
    BENCHMARK_OR_PERFORMANCE = "benchmark_or_performance"
    CONFLICT_SENSITIVE_CLAIM = "conflict_sensitive_claim"


def normalize_claim_text(text: str) -> str:
    """Normalize identity text with NFKC and collapsed Unicode whitespace."""

    return " ".join(unicodedata.normalize("NFKC", text).split())


def stable_claim_id(scope_id: str, normalized_text: str) -> str:
    """Hash an explicit scope and already-normalized claim into a stable ID."""

    normalized_scope = normalize_claim_text(scope_id)
    normalized_claim = normalize_claim_text(normalized_text)
    if not normalized_scope:
        raise ValueError("scope_id must not be empty")
    if not normalized_claim:
        raise ValueError("normalized_text must not be empty")
    payload = f"{normalized_scope}\0{normalized_claim}".encode("utf-8")
    return f"claim_{hashlib.sha256(payload).hexdigest()}"


class Claim(BaseModel):
    """An atomic factual assertion, independent of classifier and source priors.

    ``claim_id`` is SHA-256 over ``NFKC(scope_id) + NUL + normalized_text``.
    Text normalization collapses all Unicode whitespace without case folding.
    ``is_material`` is intentionally boolean because the frozen contract does not
    define a broader materiality ontology.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str = ""
    scope_id: str
    normalized_text: str
    risk_types: tuple[ClaimRiskType, ...] = ()
    is_material: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_and_identify(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        values = dict(data)
        raw_scope = values.get("scope_id")
        raw_text = values.get("normalized_text")
        if not isinstance(raw_scope, str) or not isinstance(raw_text, str):
            raise ValueError("scope_id and normalized_text must be strings")
        scope_id = normalize_claim_text(raw_scope)
        normalized_text = normalize_claim_text(raw_text)
        expected_id = stable_claim_id(scope_id, normalized_text)
        supplied_id = values.get("claim_id")
        if supplied_id and supplied_id != expected_id:
            raise ValueError("claim_id does not match normalized claim identity")
        values.update(
            scope_id=scope_id,
            normalized_text=normalized_text,
            claim_id=expected_id,
        )
        return values

    @field_validator("risk_types", mode="after")
    @classmethod
    def canonicalize_risk_types(
        cls,
        risk_types: tuple[ClaimRiskType, ...],
    ) -> tuple[ClaimRiskType, ...]:
        return tuple(dict.fromkeys(risk_types))


class Evidence(BaseModel):
    """Structured evidence preserved from the research and RAG pipeline."""

    evidence_id: str
    sub_query: str

    title: str = ""
    url: str = ""
    content: str

    source_type: str = "unknown"

    relevance_score: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
    )


class RetrievalDiagnostic(BaseModel):
    """Ranking diagnostics; authority is a source prior, never claim confidence."""

    evidence_id: str
    similarity_score: float
    authority_score: float
    final_score: float


class EvidenceContext(BaseModel):
    """RAG output containing both report context and structured evidence."""

    context: str
    evidences: list[Evidence] = Field(default_factory=list)
    retrieval_diagnostics: list[RetrievalDiagnostic] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    claim_evidence_links: list[ClaimEvidenceLink] = Field(default_factory=list)
    claim_support_summaries: list[ClaimSupportSummary] = Field(default_factory=list)


class EvidenceAssessment(BaseModel):
    """Reliability assessment for a structured evidence item."""

    evidence_id: str
    source_type: str = "unknown"

    authority_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class EvidenceConsistencyAssessment(BaseModel):
    """Cross-evidence consistency assessment for a group of evidences."""

    evidence_ids: list[str] = Field(default_factory=list)
    status: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    conflicting_evidence_ids: list[str] = Field(default_factory=list)


class ClaimEvidenceLink(BaseModel):
    """Explicit relationship whose identity is ``claim_id`` plus evidence/relation.

    ``claim`` is retained only as optional legacy display text. It is never a
    competing identity source when ``claim_id`` is present. Legacy callers that
    provide only claim text receive a deterministic ID in the ``legacy`` scope.
    """

    claim_id: str = ""
    evidence_id: str
    relation: Literal["support", "conflict", "unclear"]
    claim: str | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_legacy_claim_id(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        values = dict(data)
        if values.get("claim") is not None:
            if not isinstance(values["claim"], str):
                raise ValueError("legacy claim text must be a string")
            values["claim"] = normalize_claim_text(values["claim"])
        if not values.get("claim_id"):
            if not values.get("claim"):
                raise ValueError("claim_id is required when legacy claim text is absent")
            values["claim_id"] = stable_claim_id("legacy", values["claim"])
        return values


class ClaimSupportSummary(BaseModel):
    """Descriptive link summary; it does not authorize a claim decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    supporting_evidence_ids: tuple[str, ...] = ()
    conflicting_evidence_ids: tuple[str, ...] = ()
    unclear_evidence_ids: tuple[str, ...] = ()
    has_valid_support: bool = False
    publisher_independence_verified: bool = False
    limitation_codes: tuple[Literal["publisher_independence_metadata_unavailable"], ...] = (
        "publisher_independence_metadata_unavailable",
    )
