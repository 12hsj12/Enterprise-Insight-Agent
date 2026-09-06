"""Business orchestration; retrieval and evidence rules remain in their own layers."""

from datetime import date
from contextlib import nullcontext
from typing import Annotated, Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from gpt_researcher.evidence import (
    Evidence, EvidenceAssessment, EvidenceConsistencyAssessment,
    EvidenceConsistencyEvaluator,
)
from .trace import RunTrace


class IntelligenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target: str = Field(min_length=1, max_length=300)
    topic: str = Field(default="Competitive intelligence", min_length=1, max_length=3000)
    cutoff_date: date = date(2026, 9, 5)
    dimensions: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(default_factory=lambda: [
        "Company overview and key facts", "Products and business lines",
        "Competitors and competitive landscape", "Recent developments",
        "Evidence-backed findings, risks and uncertainties",
    ], min_length=1, max_length=12)

    def research_query(self) -> str:
        return (
            f"Analyze {self.target}: {self.topic}. Information cutoff: {self.cutoff_date.isoformat()}. "
            "Exclude developments after the cutoff; flag uncertain publication dates. "
            "Cover: " + "; ".join(self.dimensions)
        )


class IntelligenceResult(BaseModel):
    run_id: str
    request: IntelligenceRequest
    report: str
    evidences: list[Evidence]
    assessments: list[EvidenceAssessment]
    consistency: EvidenceConsistencyAssessment
    source_urls: list[str]
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    limitations: list[str] = Field(default_factory=list)
    diagnostics: dict | None = None


class IntelligenceWorkflow:
    """One research pass and one report pass, with structured provenance alongside prose."""

    def __init__(self, researcher_factory: Callable | None = None, config_path: str | None = None):
        if researcher_factory is None:
            from gpt_researcher import GPTResearcher
            researcher_factory = GPTResearcher
        self.researcher_factory = researcher_factory
        self.config_path = config_path

    async def run(self, request: IntelligenceRequest, run_id: str | None = None,
                  trace: RunTrace | None = None) -> IntelligenceResult:
        if trace is not None:
            if run_id is not None and trace.run_id != run_id:
                raise ValueError("Trace and result run IDs must match")
            run_id = trace.run_id
        with trace.activate() if trace else nullcontext():
            return await self._run(request, run_id, trace)

    async def _run(self, request, run_id, trace):
        researcher = self.researcher_factory(
            query=request.research_query(), report_type="research_report",
            report_source="web", config_path=self.config_path, verbose=False,
        )
        with trace.stage("research") if trace else nullcontext():
            await researcher.conduct_research()
        with trace.stage("report") if trace else nullcontext():
            report = await researcher.write_report(custom_prompt=(
                request.research_query() + "\nWrite a competitive intelligence report with these sections: "
                + "; ".join(request.dimensions)
                + ". Cite source URLs inline for factual claims. Distinguish source assertions, "
                "your inferences, conflicting evidence, and unknowns. A source authority prior "
                "does not establish factual correctness. Do not fill evidence gaps with invented facts."
            ))
        evidences_by_id = {}
        for evidence in researcher.get_evidences():
            previous = evidences_by_id.get(evidence.evidence_id)
            if previous is not None and previous != evidence:
                raise ValueError("Conflicting evidence objects share an evidence_id")
            evidences_by_id[evidence.evidence_id] = evidence
        evidences = list(evidences_by_id.values())
        assessments = {a.evidence_id: a for a in researcher.get_evidence_assessments()}
        if set(assessments) != set(evidences_by_id):
            raise ValueError("Evidence and reliability assessment IDs must match")
        source_urls = sorted({e.url for e in evidences if e.url})
        limitations = [
            "Claim-level support and contradiction require explicit reviewed links; consistency is insufficient without them.",
            "The cutoff is a research/report instruction, not a verified publication-date filter.",
            "Structured evidence covers the web compression path; other retrieval paths may supply report context without evidence objects.",
        ]
        if not evidences:
            limitations.append("No structured evidence was collected; report claims require manual review.")
        return IntelligenceResult(
            run_id=run_id or str(uuid4()), request=request, report=report,
            evidences=evidences, assessments=list(assessments.values()),
            consistency=EvidenceConsistencyEvaluator().evaluate(evidences),
            source_urls=source_urls, estimated_cost_usd=researcher.get_costs(),
            limitations=limitations,
            diagnostics=trace.snapshot() if trace else None,
        )
