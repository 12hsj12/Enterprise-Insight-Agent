from typing import Literal

from pydantic import BaseModel, Field


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


class EvidenceContext(BaseModel):
    """RAG output containing both report context and structured evidence."""

    context: str
    evidences: list[Evidence] = Field(default_factory=list)


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
    """Relationship between a claim and one supporting or conflicting evidence."""

    claim: str
    evidence_id: str
    relation: Literal["support", "conflict", "unclear"]