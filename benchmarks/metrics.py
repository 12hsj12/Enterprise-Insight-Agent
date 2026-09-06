"""Deterministic aggregation of explicitly reviewed quality annotations."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QualityAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewer: str = Field(min_length=1)
    method: str = Field(min_length=1, description="Human/judge identity and rubric; never inferred from link presence")
    required_facts: int = Field(ge=1)
    supported_required_facts: int = Field(ge=0)
    evaluated_citations: int = Field(ge=0)
    supporting_citations: int = Field(ge=0)
    factual_claims: int = Field(ge=0)
    claims_with_evidence: int = Field(ge=0)
    unsupported_claims: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_counts(self):
        if self.supported_required_facts > self.required_facts:
            raise ValueError("Supported required facts exceed denominator")
        if self.supporting_citations > self.evaluated_citations:
            raise ValueError("Supporting citations exceed denominator")
        if self.claims_with_evidence + self.unsupported_claims != self.factual_claims:
            raise ValueError("Every factual claim must be reviewed as supported or unsupported")
        return self


def quality_metrics(annotation: QualityAnnotation | None) -> dict[str, float | None]:
    names = ("evidence_coverage", "citation_correctness", "citation_completeness", "unsupported_claim_rate")
    if annotation is None:
        return dict.fromkeys(names)
    a = annotation
    return dict(zip(names, [
        a.supported_required_facts / a.required_facts,
        a.supporting_citations / a.evaluated_citations if a.evaluated_citations else None,
        a.claims_with_evidence / a.factual_claims if a.factual_claims else None,
        a.unsupported_claims / a.factual_claims if a.factual_claims else None,
    ]))


def summarize(records: list[dict]) -> dict:
    attempted = [r for r in records if r["status"] != "dry_run"]
    return {
        "cases": len(records), "attempted": len(attempted),
        "failures": sum(r["status"] == "failed" for r in attempted),
        "failure_rate": sum(r["status"] == "failed" for r in attempted) / len(attempted) if attempted else None,
        "mean_latency_s": sum(r["latency_s"] for r in attempted) / len(attempted) if attempted else None,
        "quality_reviewed_cases": sum(r.get("quality_annotation") is not None for r in records),
    }
