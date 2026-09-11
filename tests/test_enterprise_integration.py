"""Offline integration of the production workflow, writer, gate and renderer."""
from datetime import date
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gpt_researcher.enterprise.workflow import IntelligenceRequest, IntelligenceWorkflow
from gpt_researcher.enterprise.integration import (
    ClaimPlan, ClaimProposal, RegisteredClaimInput, integrate_claims,
    register_proposal, render_report,
)
from gpt_researcher.enterprise.trace import ResearchTrace, ResearchTraceRecorder
from gpt_researcher.evidence.models import (
    Claim, ClaimEvidenceLink, ClaimEvidenceQualification, ClaimGateContext,
    ClaimRiskType, Evidence, EvidenceContext, GroundingEvidenceAuditMetadata,
)
from gpt_researcher.evidence.reliability import EvidenceReliabilityEvaluator
from gpt_researcher.skills.writer import ReportGenerator


CUTOFF = date(2026, 9, 5)


def evidence(eid="ev_one"):
    return Evidence(evidence_id=eid, sub_query="fixture", content="Acme builds widgets.",
                    url="https://example.org/" + eid)


def item(text="Acme builds widgets.", *, risks=(), support=True, qualification=False,
         citations=("ev_one",), retry=False):
    claim = Claim(scope_id="smoke", normalized_text=text, risk_types=risks)
    return RegisteredClaimInput(
        claim=claim,
        links=[ClaimEvidenceLink(claim_id=claim.claim_id, evidence_id="ev_one", relation="support")] if support else [],
        qualifications=[ClaimEvidenceQualification(evidence_id="ev_one", is_primary_source=True)] if qualification else [],
        gate_context=ClaimGateContext(allow_retrieve_more=retry),
        cited_evidence_ids=list(citations),
    )


class FixtureResearcher:
    def __init__(self, **kwargs):
        self.query = kwargs["query"]
        self.cfg = SimpleNamespace(smart_llm_model="fixture", smart_llm_provider="fixture",
                                  smart_token_limit=4000, llm_kwargs={})
        self.report_generator = object.__new__(ReportGenerator)
        self.report_generator.researcher = self
        self.researched = False
        self.cost = 0.0

    async def conduct_research(self):
        self.researched = True

    def get_evidences(self):
        assert self.researched
        return [evidence()]

    def get_evidence_assessments(self):
        return [EvidenceReliabilityEvaluator().evaluate(evidence())]

    def get_costs(self):
        return self.cost

    def add_costs(self, cost):
        self.cost += cost


async def test_writer_workflow_artifacts_evaluation(tmp_path, monkeypatch):
    async def author(**kwargs):
        supplied = json.loads(kwargs["messages"][1]["content"])
        assert supplied["evidence"][0]["evidence_id"] == "ev_one"
        kwargs["cost_callback"](0.125)
        return json.dumps({"claims": [{"text": "Acme builds widgets.", "risk_types": [],
            "is_material": True, "relations": [{"evidence_id": "ev_one", "relation": "support"}],
            "cited_evidence_ids": ["ev_one"]}]})
    monkeypatch.setattr("gpt_researcher.utils.llm.create_chat_completion", author)
    result = await IntelligenceWorkflow(FixtureResearcher, output_directory=tmp_path).run(
        IntelligenceRequest(target="Acme", enable_v2_execution=True), run_id="smoke")
    assert result.evidence_policy is not None
    assert result.estimated_cost_usd == 0.125
    assert result.execution.evidence_context.claim_gate_results[0].decision.value == "emit"
    assert Path(result.output_artifact_reference).read_text(encoding="utf-8") == result.report
    assert hashlib.sha256(result.report.encode()).hexdigest() == result.execution.report_sha256
    assert hashlib.sha256(Path(result.output_artifact_reference).read_bytes()).hexdigest() == result.execution.report_sha256
    audit = json.loads(Path(result.execution_artifact_reference).read_text(encoding="utf-8"))
    assert "report" not in audit and audit["execution"]["evidence_context"]["context"] == ""
    trace = ResearchTrace.model_validate_json(Path(result.trace_artifact_reference).read_text(encoding="utf-8"))
    types = [e.event_type.value for e in trace.events]
    assert types[0] == "research_started" and types[-1] == "research_completed"
    assert types.index("claim_gate") < types.index("generation") < types.index("grounding_validation")
    evaluated = result.to_evaluation_case("manual-smoke")
    assert evaluated.trace_id == result.trace_id
    assert evaluated.artifact_reference == result.output_artifact_reference
    assert evaluated.benchmark_contract.passed is None


@pytest.mark.parametrize("support,risk,primary,retry,decision,mode", [
    (True, (), False, False, "emit", "factual"),
    (True, (ClaimRiskType.NUMERIC_VALUE,), False, False, "omit", None),
    (True, (ClaimRiskType.NUMERIC_VALUE,), True, False, "emit", "factual"),
    (False, (), False, False, "omit", None),
    (False, (), False, True, "retrieve_more", None),
])
def test_gate_controls_final_records(support, risk, primary, retry, decision, mode):
    plan = ClaimPlan(items=[item(risks=risk, support=support, qualification=primary, retry=retry)])
    execution = integrate_claims(EvidenceContext(context="uncontrolled prose", evidences=[evidence()]), plan, CUTOFF)
    ctx = execution.evidence_context
    assert ctx.claim_gate_results[0].decision.value == decision
    assert ctx.claim_gate_results[0].resolved_obligations is not None
    if mode:
        assert ctx.generated_claim_records[0].output_mode.value == mode
    else:
        assert ctx.generated_claim_records == []
        assert "Acme" not in render_report(execution)
    if mode == "hedged":
        assert "unconfirmed assertion" in render_report(execution)
    assert execution.additional_retrieval_attempts == 0


def test_registration_binding_and_unknown_ids():
    proposal = ClaimProposal.model_validate({"claims": [{"text": "Claim A", "risk_types": [],
        "is_material": True, "relations": [{"evidence_id": "ev_one", "relation": "support"}],
        "cited_evidence_ids": ["ev_one"]}]})
    plan = register_proposal(proposal, "stable")
    assert plan == register_proposal(proposal, "stable")
    context = EvidenceContext(context="", evidences=[evidence()])
    assert integrate_claims(context, plan, CUTOFF).evidence_context.claim_support_summaries[0].has_valid_support
    plan.items[0].links[0].evidence_id = "unknown"
    with pytest.raises(ValueError, match="Unknown evidence_id"):
        integrate_claims(context, plan, CUTOFF)
    plan.items[0].links[0].claim_id = "unknown"
    with pytest.raises(ValueError, match="registered claim"):
        integrate_claims(context, plan, CUTOFF)


def test_qualification_isolation_and_unknown_metadata():
    plan = ClaimPlan(items=[item("A has 3 widgets", risks=(ClaimRiskType.NUMERIC_VALUE,), qualification=True),
                           item("B has 4 widgets", risks=(ClaimRiskType.NUMERIC_VALUE,))])
    ctx = integrate_claims(EvidenceContext(context="", evidences=[evidence()]), plan, CUTOFF).evidence_context
    assert [g.decision.value for g in ctx.claim_gate_results] == ["emit", "omit"]
    plan.items[0].qualifications = [ClaimEvidenceQualification(evidence_id="unknown", is_primary_source=True)]
    with pytest.raises(ValueError, match="Unknown qualification"):
        integrate_claims(EvidenceContext(context="", evidences=[evidence()]), plan, CUTOFF)


@pytest.mark.parametrize("citations,dates,operation", [
    (["ev_one", "unknown"], [], "remove_invalid_citation"),
    ([], [], "remove_claim"),
    (["ev_one", "ev_two"], [], "remove_invalid_citation"),
    (["ev_one"], [GroundingEvidenceAuditMetadata(evidence_id="ev_one", publication_date=date(2026, 9, 6))], "remove_claim"),
])
def test_final_subset_and_one_repair(citations, dates, operation):
    trace = ResearchTraceRecorder(run_id="repair")
    with trace.activate():
        execution = integrate_claims(EvidenceContext(context="", evidences=[evidence(), evidence("ev_two")]),
            ClaimPlan(items=[item(citations=citations)], audit_metadata=dates), CUTOFF, trace)
    assert operation in {a.operation.value for a in execution.repair_plan.actions}
    assert sum(e.event_type.value == "repair" for e in trace.events) == len(execution.repair_plan.actions)
    assert max(r.repair_attempt for r in execution.evidence_context.grounding_validation_results) == 1
    assert all(a.operation.value in {"remove_claim", "mark_claim_hedged", "remove_invalid_citation"}
               for a in execution.repair_plan.actions)
    assert "unknown" not in render_report(execution)


@pytest.mark.parametrize("failure", ["retrieval", "generation", "registration", "export"])
async def test_failure_trace_and_no_success_artifact(tmp_path, monkeypatch, failure):
    class Broken(FixtureResearcher):
        async def conduct_research(self):
            if failure == "retrieval":
                raise ConnectionError("secret provider payload")
            await super().conduct_research()
    if failure == "generation":
        monkeypatch.setattr("gpt_researcher.utils.llm.create_chat_completion", AsyncMock(return_value="invalid JSON"))
    plan = ClaimPlan(items=[item()])
    if failure == "registration":
        plan.items.append(item())
    if failure == "export":
        (tmp_path / "failed").mkdir()
    trace = ResearchTraceRecorder(run_id="failed")
    with pytest.raises((ValueError, OSError)) if failure != "retrieval" else pytest.raises(ConnectionError):
        await IntelligenceWorkflow(Broken, output_directory=tmp_path).run(
            IntelligenceRequest(target="Acme", enable_v2_execution=True,
                                claim_plan=None if failure == "generation" else plan), trace=trace)
    payload = (tmp_path / "traces" / f"{trace.trace_id}.json").read_text(encoding="utf-8")
    failed = ResearchTrace.model_validate_json(payload)
    assert failed.execution_status.value == "failed"
    assert failed.output_artifact_reference is None
    assert "secret provider payload" not in payload
    assert not (tmp_path / "failed" / "report.md").exists()


async def test_trace_export_failure_is_fail_open(tmp_path, monkeypatch):
    trace = ResearchTraceRecorder(run_id="open")
    monkeypatch.setattr(trace, "try_export", lambda *args: None)
    result = await IntelligenceWorkflow(FixtureResearcher, output_directory=tmp_path).run(
        IntelligenceRequest(target="Acme", enable_v2_execution=True, claim_plan=ClaimPlan(items=[item()])), trace=trace)
    assert result.trace_artifact_reference is None
    assert Path(result.output_artifact_reference).exists()


def test_existing_api_exposes_integrated_result(tmp_path):
    from backend.server.enterprise_api import create_enterprise_router
    from backend.server.report_store import ReportStore
    app = FastAPI()
    app.include_router(create_enterprise_router(ReportStore(tmp_path / "tasks.json"),
        lambda: IntelligenceWorkflow(FixtureResearcher, output_directory=tmp_path)))
    with TestClient(app) as client:
        response = client.post("/api/enterprise/tasks", json=IntelligenceRequest(
            target="Acme", enable_v2_execution=True, claim_plan=ClaimPlan(items=[item()])).model_dump(mode="json"))
        assert response.status_code == 200
        body = response.json()
        assert body["result"]["execution"]["evidence_context"]["generated_claim_records"]
        assert body["result"]["trace_artifact_reference"]
        assert body["evaluation_result"]["trace_id"] == body["trace_id"]
        assert client.get("/api/enterprise/tasks/" + body["task_id"]).json() == body


def test_conflict_hedge_is_rendered_explicitly():
    registered = item("Sources disagree about Acme", risks=(ClaimRiskType.CONFLICT_SENSITIVE_CLAIM,),
                      citations=("ev_one", "ev_two"))
    registered.links.append(ClaimEvidenceLink(claim_id=registered.claim.claim_id,
                                             evidence_id="ev_two", relation="conflict"))
    registered.qualifications = [ClaimEvidenceQualification(evidence_id="ev_one", material_side_ids=("a",)),
                                 ClaimEvidenceQualification(evidence_id="ev_two", material_side_ids=("b",))]
    registered.gate_context = ClaimGateContext(required_material_side_ids=("a", "b"))
    execution = integrate_claims(EvidenceContext(context="", evidences=[evidence(), evidence("ev_two")]),
                                 ClaimPlan(items=[registered]), CUTOFF)
    assert execution.evidence_context.claim_gate_results[0].decision.value == "hedge"
    assert execution.evidence_context.generated_claim_records[0].output_mode.value == "hedged"
    assert "unconfirmed assertion" in render_report(execution)


def test_failed_api_has_evaluation_and_trace(tmp_path):
    from backend.server.enterprise_api import create_enterprise_router
    from backend.server.report_store import ReportStore
    class Broken(FixtureResearcher):
        async def conduct_research(self):
            raise ConnectionError("secret failure")
    app = FastAPI()
    app.include_router(create_enterprise_router(ReportStore(tmp_path / "tasks.json"),
        lambda: IntelligenceWorkflow(Broken, output_directory=tmp_path)))
    with TestClient(app) as client:
        response = client.post("/api/enterprise/tasks", json={"target": "Acme", "enable_v2_execution": True})
        assert response.status_code == 502
        body = response.json()
        assert body["result"] is None
        assert body["evaluation_result"]["execution_status"] == "failed"
        assert body["evaluation_result"]["artifact_reference"] is None
        assert Path(body["trace_artifact_reference"]).exists()
        assert "secret failure" not in response.text


async def test_real_gpt_researcher_search_scrape_context_writer_path(tmp_path, monkeypatch):
    from gpt_researcher import GPTResearcher
    from gpt_researcher.context.compression import ContextCompressor
    from langchain_core.documents import Document
    from langchain_community.document_transformers.embeddings_redundant_filter import get_stateful_documents

    calls = []
    class SearchFixture:
        requires_scraping = True
        def __init__(self, *args, **kwargs):
            pass
        def search(self, **kwargs):
            calls.append("search")
            return [{"href": "https://example.org/widget", "body": "Acme builds widgets."}]

    async def scrape(self, urls):
        calls.append("scrape")
        assert urls == ["https://example.org/widget"]
        return [{"url": urls[0], "raw_content": "Acme builds widgets."}]

    async def author(**kwargs):
        calls.append("write")
        data = json.loads(kwargs["messages"][1]["content"])
        eid = data["evidence"][0]["evidence_id"]
        return json.dumps({"claims": [{"text": "Acme builds widgets.", "risk_types": [],
            "is_material": True, "relations": [{"evidence_id": eid, "relation": "support"}],
            "cited_evidence_ids": [eid]}]})

    docs = get_stateful_documents([Document(page_content="Acme builds widgets.",
        metadata={"source": "https://example.org/widget"})])
    docs[0].state["query_similarity_score"] = 0.9
    # This test supplies its own retriever. Isolate registry discovery too:
    # unrelated legacy tests leave a stub retrievers.utils in sys.modules.
    monkeypatch.setattr("gpt_researcher.agent.Config.parse_retrievers", lambda self, value: ["fixture"])
    monkeypatch.setattr("gpt_researcher.agent.get_retrievers", lambda *args: [SearchFixture])
    monkeypatch.setattr("gpt_researcher.agent.Memory", lambda *args, **kwargs: SimpleNamespace(get_embeddings=lambda: None))
    monkeypatch.setattr("gpt_researcher.agent.choose_agent", AsyncMock(return_value=("Analyst", "Research")))
    monkeypatch.setattr("gpt_researcher.skills.researcher.plan_research_outline", AsyncMock(return_value=[]))
    monkeypatch.setattr("gpt_researcher.skills.browser.BrowserManager.browse_urls", scrape)
    monkeypatch.setattr("gpt_researcher.skills.image_generator.ImageGenerator.is_enabled", lambda self: False)
    monkeypatch.setattr(ContextCompressor, "_ContextCompressor__get_contextual_retriever",
                        lambda self: SimpleNamespace(invoke=lambda *args, **kwargs: docs))
    monkeypatch.setattr("gpt_researcher.utils.llm.create_chat_completion", author)
    result = await IntelligenceWorkflow(GPTResearcher, output_directory=tmp_path).run(
        IntelligenceRequest(target="Acme", topic="Verify widget business", enable_v2_execution=True), run_id="real-path")
    assert calls.index("search") < calls.index("scrape") < calls.index("write")
    assert result.retrieval_diagnostics
    assert result.execution.evidence_context.generated_claim_records
    trace = ResearchTrace.model_validate_json(Path(result.trace_artifact_reference).read_text(encoding="utf-8"))
    assert "evidence_selection" in [e.event_type.value for e in trace.events]


async def test_grounding_failure_fails_workflow(tmp_path, monkeypatch):
    from gpt_researcher.evidence.models import GroundingValidationResult, GroundingStatus
    monkeypatch.setattr("gpt_researcher.enterprise.integration.GroundingValidator.validate",
        lambda *args, **kwargs: GroundingValidationResult(status=GroundingStatus.FAIL, repair_attempt=0))
    trace = ResearchTraceRecorder(run_id="ground-failed")
    with pytest.raises(ValueError, match="Grounding validation failed"):
        await IntelligenceWorkflow(FixtureResearcher, output_directory=tmp_path).run(
            IntelligenceRequest(target="Acme", enable_v2_execution=True,
                                claim_plan=ClaimPlan(items=[item()])), trace=trace)
    saved = ResearchTrace.model_validate_json(
        (tmp_path / "traces" / f"{trace.trace_id}.json").read_text(encoding="utf-8"))
    assert saved.execution_status.value == "failed"
    assert not (tmp_path / "ground-failed" / "report.md").exists()


async def test_report_export_error_has_no_final_artifact(tmp_path, monkeypatch):
    original = Path.write_bytes
    def fail_report(path, data):
        if path.name == "report.pending":
            raise OSError("fixture disk full")
        return original(path, data)
    monkeypatch.setattr(Path, "write_bytes", fail_report)
    trace = ResearchTraceRecorder(run_id="disk-failed")
    with pytest.raises(OSError):
        await IntelligenceWorkflow(FixtureResearcher, output_directory=tmp_path).run(
            IntelligenceRequest(target="Acme", enable_v2_execution=True,
                                claim_plan=ClaimPlan(items=[item()])), trace=trace)
    saved = ResearchTrace.model_validate_json(
        (tmp_path / "traces" / f"{trace.trace_id}.json").read_text(encoding="utf-8"))
    assert saved.execution_status.value == "failed"
    assert saved.output_artifact_reference is None
    assert not (tmp_path / "disk-failed" / "report.md").exists()
