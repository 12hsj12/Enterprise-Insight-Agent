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