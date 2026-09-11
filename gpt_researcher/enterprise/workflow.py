"""Business orchestration; retrieval and evidence rules remain in their own layers."""

from datetime import date
from contextlib import nullcontext
from pathlib import Path
from typing import Annotated, Callable
from uuid import uuid4
import json
import re

from pydantic import BaseModel, ConfigDict, Field

from gpt_researcher.evidence import (
    Evidence, EvidenceAssessment, EvidenceConsistencyAssessment,
    EvidenceConsistencyEvaluator,
)
from gpt_researcher.evidence.models import RetrievalDiagnostic
from .task_policy import (
    EVIDENCE_SELECTION_LIMITATION_CODES,
    EvidencePolicy,
    ResearchTaskClassifier,
    TaskClassification,
    adaptive_authority_weight,
    evidence_policy_for,
)
from .trace import ResearchTraceRecorder
from .integration import ClaimPlan, IntegratedExecution, integrate_claims, render_report
from gpt_researcher.evidence.models import EvidenceContext


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
    enable_v2_evidence_selection: bool = False
    enable_v2_execution: bool = False
    claim_plan: ClaimPlan | None = None

    def research_intent(self) -> str:
        """Return only user-authored intent, excluding report-template expansion."""
        return f"{self.target}: {self.topic}"

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
    task_classification: TaskClassification | None = None
    evidence_policy: EvidencePolicy | None = None
    retrieval_diagnostics: list[RetrievalDiagnostic] = Field(default_factory=list)
    evidence_selection_limitation_codes: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    trace_artifact_reference: str | None = None
    output_artifact_reference: str | None = None
    execution_artifact_reference: str | None = None
    execution: IntegratedExecution | None = None

    def to_evaluation_case(self, case_id: str):
        """Expose runtime facts without manufacturing benchmark annotations."""
        from benchmarks.evaluation import EvaluationAdapter, ExecutionStatus, EfficiencyCaseMetrics
        return EvaluationAdapter.from_structured_result(
            case_id=case_id, execution_status=ExecutionStatus.COMPLETED,
            evidence_context=self.execution.evidence_context if self.execution else None,
            artifact_reference=self.output_artifact_reference,
            trace_id=self.trace_id, trace_artifact_reference=self.trace_artifact_reference,
            evidence_qualifications_available=False,
            generated_claim_records_available=self.execution is not None,
            claim_gate_available=self.execution is not None,
            grounding_available=self.execution is not None,
            efficiency=EfficiencyCaseMetrics(estimated_cost_usd=self.estimated_cost_usd),
            repaired_claim_or_output_count=(len({a.claim_id for a in self.execution.repair_plan.actions})
                if self.execution and self.execution.repair_plan
                else (0 if self.execution is not None else None)),
        )


class IntelligenceWorkflow:
    """One research pass and one report pass, with structured provenance alongside prose."""

    def __init__(self, researcher_factory: Callable | None = None, config_path: str | None = None,
                 output_directory: Path | str = "outputs/enterprise"):
        if researcher_factory is None:
            from gpt_researcher import GPTResearcher
            researcher_factory = GPTResearcher
        self.researcher_factory = researcher_factory
        self.config_path = config_path
        self.output_directory = Path(output_directory)

    async def run(self, request: IntelligenceRequest, run_id: str | None = None,
                  trace: ResearchTraceRecorder | None = None, *,
                  trace_output_directory: Path | str | None = None,
                  output_artifact_reference: str | None = None) -> IntelligenceResult:
        if request.claim_plan is not None and not request.enable_v2_execution:
            raise ValueError("claim_plan requires enable_v2_execution")
        if request.enable_v2_execution:
            run_id = run_id or (trace.run_id if trace else None) or str(uuid4())
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
                raise ValueError("Invalid artifact run ID")
            trace = trace or ResearchTraceRecorder(run_id=run_id)
            trace_output_directory = trace_output_directory or self.output_directory / "traces"
            output_artifact_reference = str(self.output_directory / run_id / "report.md")
        if trace is not None:
            if run_id is not None and trace.run_id != run_id:
                raise ValueError("Trace and result run IDs must match")
            run_id = trace.run_id
        try:
            with trace.activate() if trace else nullcontext():
                result = await self._run(
                    request, run_id, trace, output_artifact_reference
                )
                if request.enable_v2_execution:
                    directory = self.output_directory / run_id
                    directory.mkdir(parents=True, exist_ok=False)
                    execution_path = directory / "execution.json"
                    # Audit first, final report last. Failed export never advertises
                    # a final artifact through a successful result.
                    execution_path.write_text(json.dumps({
                        "run_id": run_id, "trace_id": trace.trace_id,
                        "output_artifact_reference": output_artifact_reference,
                        "execution": result.execution.model_dump(mode="json"),
                    }, ensure_ascii=False, indent=2), encoding="utf-8")
                    pending = directory / "report.pending"
                    pending.write_bytes(result.report.encode("utf-8"))
                    pending.replace(directory / "report.md")
                    result.output_artifact_reference = output_artifact_reference
                    result.execution_artifact_reference = str(execution_path)
        except BaseException as exc:
            if trace:
                terminal_trace = trace.try_fail(
                    exc, output_artifact_reference=None
                )
                if terminal_trace is not None and trace_output_directory is not None:
                    trace.try_export(trace_output_directory)
            raise

        if trace:
            terminal_trace = trace.try_complete(
                final_claim_count=(len(result.execution.evidence_context.generated_claim_records)
                                   if result.execution else None),
                output_artifact_reference=output_artifact_reference,
            )
            trace_path = (
                trace.try_export(trace_output_directory)
                if terminal_trace is not None and trace_output_directory is not None
                else None
            )
            result = result.model_copy(
                update={
                    "trace_id": trace.trace_id,
                    "trace_artifact_reference": (
                        str(trace_path) if trace_path is not None else None
                    ),
                    "diagnostics": trace.try_snapshot() or result.diagnostics,
                }
            )
        return result

    async def _run(self, request, run_id, trace, output_artifact_reference):
        task_classification = None
        evidence_policy = None
        selection_limitations = ()
        if request.enable_v2_evidence_selection or request.enable_v2_execution:
            task_classification = ResearchTaskClassifier().classify(
                request.research_intent()
            )
            evidence_policy = evidence_policy_for(task_classification.category)
            selection_limitations = EVIDENCE_SELECTION_LIMITATION_CODES
            if trace:
                trace.try_record_task_policy(
                    task_classification,
                    evidence_policy,
                    selection_limitations,
                    adaptive_authority_weight(task_classification),
                )
        researcher_kwargs = dict(
            query=request.research_query(), report_type="research_report",
            report_source="web", config_path=self.config_path, verbose=False,
        )
        if task_classification is not None and evidence_policy is not None:
            researcher_kwargs.update(
                task_classification=task_classification,
                evidence_policy=evidence_policy,
            )
        researcher = self.researcher_factory(**researcher_kwargs)
        with trace.stage("research") if trace else nullcontext():
            await researcher.conduct_research()
        if not request.enable_v2_execution:
            with trace.stage("report") if trace else nullcontext():
                report = await researcher.write_report(custom_prompt=(
                    request.research_query() + "\nWrite a competitive intelligence report with these sections: "
                    + "; ".join(request.dimensions)
                    + ". Cite source URLs inline for factual claims. Distinguish source assertions, "
                    "your inferences, conflicting evidence, and unknowns. A source authority prior "
                    "does not establish factual correctness. Do not fill evidence gaps with invented facts."
                ))
        if not request.enable_v2_execution and (not isinstance(report, str) or not report.strip()):
            raise ValueError("Research provider returned an empty report")
        if trace and not request.enable_v2_execution:
            # The legacy report writer has no typed claim hook. Record only the
            # stage outcome and optional artifact reference, never report text.
            trace.try_record_generation(
                output_artifact_reference=output_artifact_reference
            )
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
        retrieval_diagnostics_getter = getattr(
            researcher, "get_retrieval_diagnostics", None
        )
        retrieval_diagnostics = (
            list(retrieval_diagnostics_getter())
            if retrieval_diagnostics_getter is not None
            else []
        )
        execution = None
        if request.enable_v2_execution:
            context = EvidenceContext(context="", evidences=evidences,
                                      retrieval_diagnostics=retrieval_diagnostics)
            if not evidences:
                raise ValueError("No structured evidence collected")
            with trace.stage("report"):
                plan = request.claim_plan or await researcher.report_generator.plan_enterprise_claims(context, run_id)
                execution = integrate_claims(context, plan, request.cutoff_date, trace)
                report = render_report(execution)
            limitations = [
                "Structured writer relations and risk labels are authoring inputs, not independently verified semantic judgments.",
                "Qualifications are explicit claim-scoped inputs; missing metadata remains unsatisfied.",
                "No additional retrieval continuation is enabled; unresolved retrieve_more claims are excluded.",
                "Only structured web evidence is eligible; publication dates without explicit audit metadata remain unverified.",
            ]
        return IntelligenceResult(
            run_id=run_id or str(uuid4()), request=request, report=report,
            evidences=evidences, assessments=list(assessments.values()),
            consistency=EvidenceConsistencyEvaluator().evaluate(evidences),
            source_urls=source_urls, estimated_cost_usd=researcher.get_costs(),
            limitations=limitations,
            diagnostics=trace.try_snapshot() if trace else None,
            task_classification=task_classification,
            evidence_policy=evidence_policy,
            retrieval_diagnostics=retrieval_diagnostics,
            evidence_selection_limitation_codes=list(selection_limitations),
            trace_id=trace.trace_id if trace else None,
            execution=execution,
        )
