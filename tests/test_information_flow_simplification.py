"""Offline boundaries for the restored Writer-first Enterprise V2 flow."""

from datetime import date
from pathlib import Path

import pytest

from gpt_researcher.enterprise.integration import (
    ClaimPlan, RegisteredClaimInput, integrate_claims, render_report,
    restrict_claim_plan_to_draft,
)
from gpt_researcher.enterprise.layered_output import EvidenceGroundedInference
from gpt_researcher.enterprise.requirements import (
    RequirementType, ResearchRequirement, fallback_research_plan,
)
from gpt_researcher.enterprise.workflow import IntelligenceRequest, IntelligenceWorkflow
from gpt_researcher.evidence.models import (
    Claim, ClaimEvidenceLink, ClaimRiskType, Evidence, EvidenceContext,
)
from gpt_researcher.evidence.reliability import EvidenceReliabilityEvaluator


CUTOFF = date(2026, 9, 5)


def requirement(rid: str, text: str, kind: RequirementType,
                order: int) -> ResearchRequirement:
    return ResearchRequirement(requirement_id=rid, text=text,
                               requirement_type=kind, order=order)


def linked_claim(text: str, requirement_id: str, evidences: list[Evidence],
                 risks=()) -> RegisteredClaimInput:
    claim = Claim(scope_id="information-flow", normalized_text=text,
                  risk_types=risks)
    return RegisteredClaimInput(
        claim=claim, requirement_id=requirement_id,
        links=[ClaimEvidenceLink(claim_id=claim.claim_id,
                                 evidence_id=source.evidence_id,
                                 relation="support") for source in evidences],
        cited_evidence_ids=[source.evidence_id for source in evidences],
    )


def test_generic_topic_cannot_replace_cc_question_or_ed_recommendation():
    cc_target = "比较 AWS Bedrock 与 Azure OpenAI 的模型选择和定价透明度。"
    cc = fallback_research_plan(target=cc_target, topic="Development research",
                                dimensions=["模型选择对比", "定价透明度对比"],
                                cutoff_date=CUTOFF, reason="fixture")
    assert all(cc_target in item.text for item in cc.requirements)
    assert all("Development research" not in item.query for item in cc.sub_queries)
    assert cc.requirements[0].requirement_type is RequirementType.COMPARATIVE

    ed_target = "为制造企业选择 pgvector 或 Milvus，并提出迁移建议。"
    ed = fallback_research_plan(target=ed_target, topic="Development research",
                                dimensions=["候选技术能力", "条件化迁移建议"],
                                cutoff_date=CUTOFF, reason="fixture")
    assert ed.requirements[1].requirement_type is RequirementType.RECOMMENDATION
    assert ed.requirements[1].text.startswith(ed_target)


def test_binding_call_cannot_add_a_fact_absent_from_full_writer_draft():
    source = Evidence(evidence_id="one", sub_query="fixture",
                      content="Acme builds widgets.", url="https://example.test/one")
    present = linked_claim("Acme builds widgets.", "R1", [source])
    invented = linked_claim("Acme released a new widget in 2026.", "R1", [source])
    plan = ClaimPlan(items=[present, invented])
    restricted = restrict_claim_plan_to_draft(
        plan, "## Business\n\nAcme builds widgets. ([source](https://example.test/one))"
    )
    assert [item.claim.claim_id for item in restricted.items] == [present.claim.claim_id]
    assert restricted.invalid_draft_claim_input_count == 1
    denied = restrict_claim_plan_to_draft(
        ClaimPlan(items=[present]), "It is false that Acme builds widgets."
    )
    assert denied.items == []


def test_draft_binding_accepts_atomic_claim_from_composite_sentence():
    source = Evidence(evidence_id="one", sub_query="fixture",
                      content="AWS supports models from A.",
                      url="https://example.test/one")
    extracted = linked_claim("AWS supports models from A.", "R1", [source])
    plan = restrict_claim_plan_to_draft(
        ClaimPlan(items=[extracted]),
        "AWS SUPPORTS models from A, while Azure supports models from B.",
    )
    assert [item.claim.claim_id for item in plan.items] == [extracted.claim.claim_id]
    assert plan.invalid_draft_claim_input_count == 0


@pytest.mark.parametrize(("draft", "claim_text"), [
    ("Acme cannot support private networking.", "support private networking."),
    ("Acme can't support private networking.", "support private networking."),
    ("Acme doesn't support private networking.", "support private networking."),
    ("Acme fails to support private networking.", "support private networking."),
    ("该平台不支持私有网络。", "支持私有网络。"),
    ("The capability is unsupported.", "supported."),
    ("The results are incomparable.", "comparable."),
])
def test_draft_binding_does_not_reverse_negated_claims(draft, claim_text):
    source = Evidence(evidence_id="one", sub_query="fixture",
                      content=claim_text, url="https://example.test/one")
    proposed = linked_claim(claim_text, "R1", [source])
    restricted = restrict_claim_plan_to_draft(ClaimPlan(items=[proposed]), draft)
    assert restricted.items == []
    assert restricted.invalid_draft_claim_input_count == 1


def test_comparison_discloses_both_literal_sources_without_reviving_gate_claim():
    aws = Evidence(evidence_id="aws", sub_query="cc", url="https://aws.example/docs",
                   content="AWS Bedrock lists models from multiple providers.")
    azure = Evidence(evidence_id="azure", sub_query="cc", url="https://azure.example/docs",
                     content="Azure OpenAI lists models available to enterprise users.")
    claim = linked_claim(
        "AWS Bedrock and Azure OpenAI differ in model choice.", "R1",
        [aws, azure], risks=(ClaimRiskType.COMPARATIVE_CLAIM,),
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[aws, azure]),
        ClaimPlan(items=[claim], requirements=[requirement(
            "R1", "比较 AWS Bedrock 与 Azure OpenAI 的模型选择", RequirementType.FACTUAL, 1
        )]), CUTOFF,
    )
    assert execution.evidence_context.claim_gate_results[0].decision.value == "omit"
    assert execution.evidence_context.generated_claim_records == []
    assert len(execution.limited_disclosures) == 2
    report = render_report(execution, writer_draft=(
        "## Model choice\n\nAWS Bedrock and Azure OpenAI differ in model choice."
    ))
    assert "AWS Bedrock lists models" in report
    assert "Azure OpenAI lists models" in report
    assert "AWS Bedrock and Azure OpenAI differ in model choice" not in report
    assert "LIMITED_EVIDENCE" in report


def test_chinese_direct_source_passage_can_be_disclosed_safely():
    source = Evidence(
        evidence_id="cn", sub_query="cc", url="https://example.test/cn",
        content="厂商资料说明该平台支持企业网络隔离。该说明未经过第三方验证。",
    )
    claim = linked_claim("该平台支持企业网络隔离。", "R1", [source],
                         risks=(ClaimRiskType.COMPARATIVE_CLAIM,))
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(items=[claim], requirements=[requirement(
            "R1", "网络隔离对比", RequirementType.FACTUAL, 1
        )]), CUTOFF,
    )
    assert [item.excerpt for item in execution.limited_disclosures] == [
        "厂商资料说明该平台支持企业网络隔离。"
    ]


def test_direct_source_disclosure_does_not_require_checklist_assignment():
    source = Evidence(
        evidence_id="unassigned", sub_query="context",
        url="https://example.test/unassigned",
        content="Vendor documentation states that the platform supports private networking.",
    )
    claim = linked_claim(
        "The platform supports private networking.", "R1", [source],
        risks=(ClaimRiskType.COMPARATIVE_CLAIM,),
    ).model_copy(update={"requirement_id": None})
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[claim]), CUTOFF,
    )
    assert [item.excerpt for item in execution.limited_disclosures] == [
        "Vendor documentation states that the platform supports private networking."
    ]
    assert execution.limited_disclosures[0].requirement_id is None


def test_ed_conditional_advice_requires_surviving_premise_and_cites_it():
    source = Evidence(evidence_id="pg", sub_query="ed", url="https://example.test/pg",
                      content="pgvector offers HNSW indexing.")
    fact = linked_claim("pgvector offers HNSW indexing.", "R1", [source])
    inference = EvidenceGroundedInference(
        inference_id="pilot", requirement_id="R2",
        text="If operations remain small, consider pgvector.",
        premise_claim_ids=(fact.claim.claim_id,),
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(items=[fact], inferences=[inference], requirements=[
            requirement("R1", "候选技术能力", RequirementType.FACTUAL, 1),
            requirement("R2", "条件化迁移建议", RequirementType.RECOMMENDATION, 2),
        ]), CUTOFF,
    )
    assert execution.layered_output_summary["ai_inference"] == 1
    report = render_report(execution, writer_draft=(
        "## Candidate capability\n\npgvector offers HNSW indexing."
    ))
    assert "AI_INFERENCE" in report
    assert "consider pgvector" in report
    assert "前提来源" in report and "https://example.test/pg" in report


def test_unbound_high_risk_draft_fact_is_not_published():
    execution = integrate_claims(EvidenceContext(context="", evidences=[]),
                                 ClaimPlan(items=[]), CUTOFF)
    report = render_report(execution, writer_draft=(
        "## Market overview\n\nAcme captured 87% market share in 2026."
    ))
    assert "87%" not in report
    assert "未通过逐句来源核查" in report
    escaped = render_report(execution, writer_draft=(
        "## <script>alert(1)</script>\n\nAcme captured 87% market share in 2026."
    ))
    assert "<script>" not in escaped


@pytest.mark.asyncio
async def test_workflow_uses_complete_research_context_before_existing_audit(tmp_path):
    class Researcher:
        targeted_calls = 0

        def __init__(self, **kwargs):
            assert "requirement_planning_context" not in kwargs
            self.query = kwargs["query"]
            self.context = "Acme builds widgets. Additional full research context."
            self.research_plan = None
            self.researched = False
            self.evidence = Evidence(
                evidence_id="one", sub_query="fixture", url="https://example.test/one",
                content="Acme builds widgets.",
            )
            self.report_generator = self

        async def conduct_research(self):
            self.researched = True

        async def write_report(self, **kwargs):
            assert self.researched
            assert "Additional full research context" in self.context
            return "## Business\n\nAcme builds widgets. ([source](https://example.test/one))"

        async def plan_enterprise_claims(self, context, scope_id, draft, coverage_plan):
            assert "Acme builds widgets" in draft
            assert "Additional full research context" not in context.evidences[0].content
            assert "Acme" in coverage_plan.requirements[0].text
            return ClaimPlan(
                items=[linked_claim("Acme builds widgets.", "R1", [self.evidence])],
                requirements=list(coverage_plan.requirements),
            )

        async def conduct_targeted_research(self, queries):
            self.__class__.targeted_calls += 1
            raise AssertionError("Automatic second retrieval must not run")

        def get_evidences(self):
            return [self.evidence]

        def get_evidence_assessments(self):
            return [EvidenceReliabilityEvaluator().evaluate(self.evidence)]

        def get_costs(self):
            return 0.0

    result = await IntelligenceWorkflow(Researcher, output_directory=tmp_path).run(
        IntelligenceRequest(target="Acme", topic="Development research",
                            dimensions=["business"], enable_v2_execution=True),
        run_id="writer-first",
    )
    assert Researcher.targeted_calls == 0
    assert result.second_retrieval.queries_count == 0
    assert "VERIFIED_FACT" in result.report
    assert Path(result.writer_draft_artifact_reference).read_text(encoding="utf-8")
    assert result.execution.writer_draft_sha256
    assert result.diagnostics["invalid_draft_claim_input_count"] == 0
