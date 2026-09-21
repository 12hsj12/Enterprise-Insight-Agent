"""Batch 4 offline contract fixtures; no provider, search, or benchmark calls."""

from datetime import date
import json
from types import SimpleNamespace

import pytest

from gpt_researcher.enterprise.integration import (
    ClaimPlan, ClaimProposal, RegisteredClaimInput, integrate_claims, propose_claims,
    register_proposal, render_report,
)
from gpt_researcher.enterprise.layered_output import (
    EvidenceGroundedInference, OutputMode, SourceExcerpt,
)
from gpt_researcher.enterprise.requirements import RequirementType, ResearchRequirement
from gpt_researcher.evidence.models import (
    Claim, ClaimEvidenceLink, ClaimEvidenceQualification, ClaimRiskType,
    ClaimGateContext, Evidence, EvidenceContext, GroundingEvidenceAuditMetadata,
)


CUTOFF = date(2026, 9, 5)


def req(rid="R1", kind=RequirementType.FACTUAL):
    return ResearchRequirement(requirement_id=rid, text=f"Question {rid}",
                               requirement_type=kind, order=int(rid[1:]),
                               target_entities=("A", "B") if kind is RequirementType.COMPARATIVE else ())


def ev(eid="e1", content="A vendor documentation reports latency of 10 ms.",
       publisher="Vendor A", publication_date=None):
    return Evidence(evidence_id=eid, sub_query="fixture", content=content,
                    url=f"https://example.org/{eid}", publisher=publisher,
                    publication_date=publication_date)


def item(text="A has measured latency of 10 ms.", *, rid="R1", eid="e1",
         risks=(ClaimRiskType.BENCHMARK_OR_PERFORMANCE,), relation="support",
         citations=None, qualifications=()):
    claim = Claim(scope_id="layered", normalized_text=text, risk_types=risks)
    return RegisteredClaimInput(
        claim=claim, requirement_id=rid,
        links=[ClaimEvidenceLink(claim_id=claim.claim_id, evidence_id=eid, relation=relation)],
        qualifications=list(qualifications),
        cited_evidence_ids=[eid] if citations is None else list(citations),
    )


def run(items, evidences, *, requirements=None, excerpts=(), inferences=(), dates=(), invalid=0):
    plan = ClaimPlan(items=list(items), requirements=list(requirements or [req()]),
                     source_excerpts=list(excerpts), inferences=list(inferences),
                     audit_metadata=list(dates), invalid_inference_input_count=invalid)
    result = integrate_claims(EvidenceContext(context="", evidences=list(evidences)), plan, CUTOFF)
    return result, render_report(result)


def quote(registered, excerpt="A vendor documentation reports latency of 10 ms.", eid="e1"):
    return SourceExcerpt(claim_id=registered.claim.claim_id,
                         requirement_id=registered.requirement_id,
                         evidence_id=eid, excerpt=excerpt)


def test_t01_gate_emit_grounding_pass_is_normal_verified_fact():
    registered = item("A documentation describes widgets.", risks=())
    result, report = run([registered], [ev(content="A documentation describes widgets.")])
    assert result.evidence_context.claim_gate_results[0].decision.value == "emit"
    assert result.layered_output_summary["verified_fact"] == 1
    assert "A documentation describes widgets" in report


def test_grounding_strength_failure_downgrades_to_literal_limited_evidence():
    registered = item(
        "Traffic never traverses the public internet.", risks=()
    )
    source = ev(content="Vendor documentation states that traffic uses a private endpoint.")
    result, _ = run(
        [registered], [source],
        excerpts=[quote(
            registered,
            "Vendor documentation states that traffic uses a private endpoint.",
        )],
    )
    report = render_report(
        result,
        writer_draft="## Networking\n\nTraffic never traverses the public internet.",
    )
    assert result.evidence_context.claim_gate_results[0].decision.value == "emit"
    assert result.layered_output_summary["verified_fact"] == 0
    assert result.layered_output_summary["limited_evidence"] == 1
    assert "Traffic never traverses" not in report
    assert "traffic uses a private endpoint" in report
    assert "LIMITED_EVIDENCE" in report


def test_limited_premise_can_support_conditional_inference_with_visible_strength():
    premise = item("pgvector has unlimited scale.")
    source = ev(content="Vendor documentation states that pgvector is a PostgreSQL extension.")
    candidate = EvidenceGroundedInference(
        inference_id="i-limited", requirement_id="R2",
        text="If operational simplicity is the priority, consider pgvector.",
        premise_claim_ids=(premise.claim.claim_id,),
    )
    plan = ClaimPlan(
        items=[premise],
        requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
        source_excerpts=[quote(
            premise,
            "Vendor documentation states that pgvector is a PostgreSQL extension.",
        )],
        inferences=[candidate],
    )
    result = integrate_claims(
        EvidenceContext(context="", evidences=[source]), plan, CUTOFF,
    )
    report = render_report(
        result,
        writer_draft=(
            "## Candidate\n\npgvector has unlimited scale.\n\n"
            "## Decision\n\nChoose pgvector for production."
        ),
    )
    assert result.layered_output_summary["verified_fact"] == 0
    assert result.layered_output_summary["limited_evidence"] == 1
    assert result.layered_output_summary["ai_inference"] == 1
    assert "pgvector has unlimited scale" not in report
    assert "Choose pgvector for production" not in report
    assert "AI_INFERENCE" in report
    assert "前提强度：LIMITED_EVIDENCE" in report
    assert "Vendor documentation states that pgvector is a PostgreSQL extension" in report


def test_t02_direct_support_missing_independent_is_limited_not_verified():
    registered = item()
    result, report = run([registered], [ev()], excerpts=[quote(registered)])
    assert result.evidence_context.claim_gate_results[0].decision.value == "omit"
    assert result.layered_output_summary == dict(verified_fact=0, limited_evidence=1,
                                                  ai_inference=0, unresolved=0)
    assert registered.claim.normalized_text not in report
    assert "vendor documentation reports latency" in report


def test_t03_source_authority_does_not_upgrade_limited():
    registered = item()
    source = ev()
    source.relevance_score = 1.0
    result, report = run([registered], [source], excerpts=[quote(registered)])
    assert result.layered_output_summary["verified_fact"] == 0
    assert "Vendor A 的资料" not in report  # Publisher provenance is unknown.
    assert "Source e1 的资料" in report


def test_unknown_publisher_metadata_remains_neutral_after_registration():
    proposal = ClaimProposal.model_validate({
        "claims": [{"claim_reference_id": "c1", "requirement_id": "R1",
                    "text": "A objectively outperforms B.",
                    "risk_types": ["benchmark_or_performance"], "is_material": True,
                    "relations": [{"evidence_id": "e1", "relation": "support"}],
                    "cited_evidence_ids": ["e1"]}],
        "source_excerpts": [{"claim_reference_id": "c1", "evidence_id": "e1",
                            "excerpt": "A vendor documentation reports latency of 10 ms."}],
    })
    source = ev(publisher="Official A")
    plan = register_proposal(proposal, "layered", [source], [req()])
    assert plan.source_identity_resolutions[0].status == "resolved_explicit_metadata"
    result = integrate_claims(EvidenceContext(context="", evidences=[source]), plan, CUTOFF)
    report = render_report(result)
    assert "Official A 的资料" not in report
    assert "Source e1 的资料" in report


def test_t04_vendor_benchmark_is_only_attributed():
    registered = item("A objectively outperforms B.")
    result, report = run([registered], [ev()], excerpts=[quote(registered)])
    assert "A objectively outperforms B" not in report
    assert result.layered_output_summary["limited_evidence"] == 1
    assert "证据说明" in report


def test_t05_two_vendor_sides_visible_without_adjudicator():
    first = item("A is faster than B.", risks=(ClaimRiskType.CONFLICT_SENSITIVE_CLAIM,))
    first.links.append(ClaimEvidenceLink(claim_id=first.claim.claim_id,
                                         evidence_id="e2", relation="conflict"))
    first.qualifications = [ClaimEvidenceQualification(evidence_id="e1", material_side_ids=("a",)),
                            ClaimEvidenceQualification(evidence_id="e2", material_side_ids=("b",))]
    first.gate_context = ClaimGateContext(required_material_side_ids=("a", "b"))
    first.cited_evidence_ids = ["e1", "e2"]
    second = item("B is faster than A.", eid="e2")
    source_b = ev("e2", "B vendor documentation reports latency of 12 ms.", "Vendor B")
    result, report = run([first, second], [ev(), source_b], requirements=[req()],
                         excerpts=[quote(first), quote(second,
                                         "B vendor documentation reports latency of 12 ms.", "e2")])
    assert result.evidence_context.claim_gate_results[0].decision.value == "hedge"
    assert result.layered_output_summary["limited_evidence"] == 2
    assert result.layered_output_summary["unresolved"] == 1
    assert "10 ms" in report and "12 ms" in report
    assert "A is faster than B" not in report and "B is faster than A" not in report
    assert "双方说法存在冲突" in report and "当前无法确认哪一方" in report


def test_t06_no_support_is_unresolved_even_with_literal_excerpt():
    registered = item(relation="unclear")
    result, report = run([registered], [ev()], excerpts=[quote(registered)])
    assert result.layered_output_summary["unresolved"] == 1
    assert "10 ms" not in report


@pytest.mark.parametrize("relation", ["conflict", "unclear"])
def test_t07_t08_conflict_or_unclear_relation_cannot_be_limited_support(relation):
    registered = item(relation=relation)
    result, _ = run([registered], [ev()], excerpts=[quote(registered)])
    assert result.limited_disclosures == []


def test_t09_wrong_requirement_scope_cannot_reuse_excerpt():
    registered = item()
    wrong = quote(registered).model_copy(update={"requirement_id": "R9"})
    result, _ = run([registered], [ev()], excerpts=[wrong])
    assert result.limited_disclosures == []


def test_t10_nonliteral_writer_excerpt_fails_closed():
    registered = item()
    bad = quote(registered, "A has a latency of 1 ms.")
    result, _ = run([registered], [ev()], excerpts=[bad])
    assert result.limited_disclosures == []


@pytest.mark.parametrize("content,fragment", [
    ("A has not migrated to PostgreSQL.", "migrated to PostgreSQL."),
    ("Do not claim that A is faster than B.", "A is faster than B."),
    ("The vendor denies that A is faster than B. A remains under review.",
     "A is faster than B."),
])
def test_negated_or_denied_source_fragment_cannot_be_disclosed(content, fragment):
    rejected = item("A is objectively faster than B.")
    result, report = run([rejected], [ev(content=content)],
                         excerpts=[quote(rejected, fragment)])
    assert result.evidence_context.claim_gate_results[0].decision.value != "emit"
    assert result.limited_disclosures == []
    assert fragment not in report
    assert result.layered_output_summary["unresolved"] == 1


def test_complete_negated_source_sentence_can_be_attributed_without_emitting_claim():
    rejected = item("A has migrated to PostgreSQL.")
    denial = "A has not migrated to PostgreSQL."
    result, report = run([rejected], [ev(content=denial)],
                         excerpts=[quote(rejected, denial)])
    assert result.layered_output_summary["verified_fact"] == 0
    assert result.layered_output_summary["limited_evidence"] == 1
    assert result.limited_disclosures[0].excerpt == denial
    assert denial.replace(".", "\\.") in report
    assert rejected.claim.normalized_text not in report


def test_t11_missing_final_citation_cannot_be_limited():
    registered = item(citations=[])
    result, _ = run([registered], [ev()], excerpts=[quote(registered)])
    assert result.limited_disclosures == []


def test_t12_post_cutoff_source_cannot_be_limited():
    registered = item()
    result, _ = run([registered], [ev()], excerpts=[quote(registered)],
                    dates=[GroundingEvidenceAuditMetadata(evidence_id="e1", publication_date=date(2026, 9, 6))])
    assert result.limited_disclosures == []


def test_t13_unknown_date_is_source_attribution_without_current_claim():
    registered = item("A is currently faster than B.")
    result, report = run([registered], [ev()], excerpts=[quote(registered)])
    assert result.layered_output_summary["limited_evidence"] == 1
    assert "A is currently faster than B" not in report
    assert "发布日期未得到可靠验证" in report


def test_t14_exact_rejected_claim_copy_cannot_be_disclosed():
    registered = item("A vendor documentation reports latency of 10 ms.")
    result, _ = run([registered], [ev()], excerpts=[quote(registered)])
    assert result.limited_disclosures == []


def test_t15_fully_verified_section_has_no_labels_or_warning():
    registered = item("A documentation describes widgets.", risks=())
    _, report = run([registered], [ev(content="A documentation describes widgets.")])
    assert "证据说明" not in report and "AI 分析" not in report


def test_t16_factual_only_requirement_has_no_analysis():
    registered = item("A documentation describes widgets.", risks=())
    candidate = EvidenceGroundedInference(inference_id="i1", requirement_id="R1",
                                          text="This suggests option A.",
                                          premise_claim_ids=(registered.claim.claim_id,))
    result, report = run([registered], [ev(content="A documentation describes widgets.")],
                         inferences=[candidate])
    assert result.surviving_inferences == [] and "AI 分析" not in report


def test_t17_recommendation_with_surviving_premise_is_ai_analysis():
    registered = item("Product A supports widgets.", risks=())
    candidate = EvidenceGroundedInference(inference_id="i1", requirement_id="R2",
                                          text="Based on this deployment premise, first validate A.",
                                          premise_claim_ids=(registered.claim.claim_id,))
    result, report = run([registered], [ev(content="Product A supports widgets.")],
                         requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
                         inferences=[candidate])
    assert result.layered_output_summary["ai_inference"] == 1
    assert "AI 分析" in report


def test_single_recommendation_section_can_mix_all_three_visible_modes():
    premise = item("Product A supports widgets.", risks=())
    limited = item("B objectively outperforms A.", eid="e2")
    candidate = EvidenceGroundedInference(
        inference_id="i1", requirement_id="R1", text="Based on the deployment premise, validate A first.",
        premise_claim_ids=(premise.claim.claim_id,),
    )
    result, report = run(
        [premise, limited],
        [ev(content="Product A supports widgets."),
         ev("e2", "B vendor documentation reports latency of 12 ms.", "Vendor B")],
        requirements=[req(kind=RequirementType.RECOMMENDATION)],
        excerpts=[quote(limited, "B vendor documentation reports latency of 12 ms.", "e2")],
        inferences=[candidate],
    )
    assert result.layered_output_summary == dict(
        verified_fact=1, limited_evidence=1, ai_inference=1, unresolved=0)
    assert report.count("## Question R1") == 1
    assert "证据说明" in report and "AI 分析" in report


def test_t18_unknown_premise_fails_closed():
    registered = item("A documentation describes widgets.", risks=())
    candidate = EvidenceGroundedInference(inference_id="i1", requirement_id="R2",
                                          text="Validate A first.", premise_claim_ids=("unknown",))
    result, _ = run([registered], [ev(content="A documentation describes widgets.")],
                    requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
                    inferences=[candidate])
    assert result.inference_validation_summary.premise_failure_count == 1
    assert result.layered_output_summary["verified_fact"] == 1


def test_t19_premise_removed_by_grounding_repair_drops_inference():
    registered = item("A documentation describes widgets.", risks=(), citations=[])
    candidate = EvidenceGroundedInference(inference_id="i1", requirement_id="R2",
                                          text="Validate A first.",
                                          premise_claim_ids=(registered.claim.claim_id,))
    result, _ = run([registered], [ev(content="A documentation describes widgets.")],
                    requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
                    inferences=[candidate])
    assert result.repair_plan is not None
    assert result.surviving_inferences == []
    assert result.inference_validation_summary.premise_failure_count == 1


def test_t20_new_numeric_fact_in_inference_is_discarded_without_losing_fact():
    registered = item("A documentation describes widgets.", risks=())
    candidate = EvidenceGroundedInference(inference_id="i1", requirement_id="R2",
                                          text="A raises revenue by 30%, so select it.",
                                          premise_claim_ids=(registered.claim.claim_id,))
    result, report = run([registered], [ev(content="A documentation describes widgets.")],
                         requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
                         inferences=[candidate])
    assert "30%" not in report
    assert result.inference_validation_summary.invalid_inference_count == 1
    assert result.layered_output_summary["verified_fact"] == 1


def test_unsupported_company_action_in_inference_is_discarded():
    premise = item("pgvector is a PostgreSQL extension.", risks=())
    candidate = EvidenceGroundedInference(
        inference_id="i1", requirement_id="R2",
        text="Company A has already migrated its production stack to PostgreSQL, so choose pgvector.",
        premise_claim_ids=(premise.claim.claim_id,),
    )
    result, report = run(
        [premise], [ev(content="pgvector is a PostgreSQL extension.")],
        requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
        inferences=[candidate],
    )
    assert result.inference_validation_summary.invalid_inference_count == 1
    assert "Company A has already migrated" not in report
    assert result.layered_output_summary["verified_fact"] == 1


@pytest.mark.parametrize("premise_text,target", [
    ("This is a PostgreSQL extension.", "A"),
    ("A PostgreSQL extension is available.", "A"),
    ("It supports widgets for us.", "IT"),
    ("It supports widgets for us.", "US"),
    ("Please help US.", "US"),
    ("Please review IT.", "IT"),
])
def test_article_or_pronoun_is_not_an_inference_action_target(premise_text, target):
    premise = item(premise_text, risks=())
    candidate = EvidenceGroundedInference(
        inference_id="i1", requirement_id="R2", text=f"Choose {target}.",
        premise_claim_ids=(premise.claim.claim_id,),
    )
    result, report = run(
        [premise], [ev(content=premise_text)],
        requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
        inferences=[candidate],
    )
    assert result.layered_output_summary["verified_fact"] == 1
    assert result.surviving_inferences == []
    assert result.inference_validation_summary.invalid_inference_count == 1
    assert f"Choose {target}." not in report


@pytest.mark.parametrize("premise_text,target", [
    ("Product A supports widgets.", "A"),
    ("A supports widgets.", "A"),
    ("US supports widgets.", "US"),
    ("IT supports widgets.", "IT"),
])
def test_explicit_premise_entity_preserves_grounded_recommendation(premise_text, target):
    premise = item(premise_text, risks=())
    candidate = EvidenceGroundedInference(
        inference_id="i1", requirement_id="R2", text=f"Choose {target}.",
        premise_claim_ids=(premise.claim.claim_id,),
    )
    result, report = run(
        [premise], [ev(content=premise_text)],
        requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
        inferences=[candidate],
    )
    assert result.layered_output_summary["verified_fact"] == 1
    assert result.layered_output_summary["ai_inference"] == 1
    assert result.surviving_inferences[0].text == f"Choose {target}."
    assert f"Choose {target}\\." in report


def test_conditional_recommendation_uses_surviving_premise_without_new_fact():
    premise = item("pgvector is a PostgreSQL extension.", risks=())
    candidate = EvidenceGroundedInference(
        inference_id="i1", requirement_id="R2",
        text="If operational simplicity is the priority, consider pgvector.",
        premise_claim_ids=(premise.claim.claim_id,),
    )
    result, report = run(
        [premise], [ev(content="pgvector is a PostgreSQL extension.")],
        requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
        inferences=[candidate],
    )
    assert result.layered_output_summary["ai_inference"] == 1
    assert "If operational simplicity is the priority, consider pgvector" in report


def test_conditional_cannot_hide_a_second_declarative_sentence():
    premise = item("pgvector is a PostgreSQL extension.", risks=())
    candidate = EvidenceGroundedInference(
        inference_id="i1", requirement_id="R2",
        text="If simplicity matters. Company A has already migrated, choose pgvector.",
        premise_claim_ids=(premise.claim.claim_id,),
    )
    result, report = run(
        [premise], [ev(content="pgvector is a PostgreSQL extension.")],
        requirements=[req(), req("R2", RequirementType.RECOMMENDATION)],
        inferences=[candidate],
    )
    assert result.inference_validation_summary.invalid_inference_count == 1
    assert "Company A has already migrated" not in report


def test_tradeoff_action_can_compare_two_surviving_premise_entities():
    first = item("pgvector is a PostgreSQL extension.", risks=())
    second = item("Milvus is a vector database.", rid="R2", eid="e2", risks=())
    candidate = EvidenceGroundedInference(
        inference_id="i1", requirement_id="R3", text="Compare pgvector and Milvus.",
        premise_claim_ids=(first.claim.claim_id, second.claim.claim_id),
    )
    result, report = run(
        [first, second],
        [ev(content="pgvector is a PostgreSQL extension."),
         ev("e2", "Milvus is a vector database.")],
        requirements=[req(), req("R2"), req("R3", RequirementType.RECOMMENDATION)],
        inferences=[candidate],
    )
    assert result.layered_output_summary["ai_inference"] == 1
    assert "Compare pgvector and Milvus against the decision requirements" in report


def test_inference_invalid_structure_count_does_not_break_facts():
    registered = item("A documentation describes widgets.", risks=())
    result, _ = run([registered], [ev(content="A documentation describes widgets.")], invalid=1)
    assert result.inference_validation_summary.invalid_inference_count == 1
    assert result.layered_output_summary["verified_fact"] == 1


def test_closed_four_output_modes():
    assert set(OutputMode) == {OutputMode.VERIFIED_FACT, OutputMode.LIMITED_EVIDENCE,
                               OutputMode.AI_INFERENCE, OutputMode.UNRESOLVED}


async def test_malformed_writer_inference_is_isolated_from_fact_path(monkeypatch):
    calls = 0

    async def author(**kwargs):
        nonlocal calls
        calls += 1
        return json.dumps({
            "claims": [{"claim_reference_id": "c1", "requirement_id": "R1",
                        "text": "A documentation describes widgets.", "risk_types": [],
                        "is_material": True, "relations": [{"evidence_id": "e1", "relation": "support"}],
                        "cited_evidence_ids": ["e1"]}],
            "inferences": [{"inference_id": "broken", "requirement_id": "R2",
                            "text": "Recommend A.", "premise_claim_ids": []}],
        })

    monkeypatch.setattr("gpt_researcher.utils.llm.create_chat_completion", author)
    researcher = SimpleNamespace(query="fixture", cfg=SimpleNamespace(
        smart_llm_model="fixture", smart_llm_provider="fixture", smart_token_limit=5000,
        llm_kwargs={}), add_costs=lambda value: None,
        research_plan=SimpleNamespace(requirements=(req(), req("R2", RequirementType.RECOMMENDATION))))
    context = EvidenceContext(context="", evidences=[ev(content="A documentation describes widgets.")])
    plan = await propose_claims(researcher, context, "layered")
    result = integrate_claims(context, plan, CUTOFF)
    assert calls == 1
    assert result.layered_output_summary["verified_fact"] == 1
    assert result.inference_validation_summary.invalid_inference_count == 1


@pytest.mark.asyncio
async def test_malformed_writer_claim_and_source_identity_do_not_abort_valid_claim(monkeypatch):
    async def author(**kwargs):
        return json.dumps({
            "claims": [
                {"claim_reference_id": "good", "requirement_id": "R1",
                 "text": "A documentation describes widgets.", "risk_types": [],
                 "is_material": True,
                 "relations": [{"evidence_id": "e1", "relation": "support"}],
                 "cited_evidence_ids": ["e1"]},
                {"claim_reference_id": "bad", "requirement_id": "R1",
                 "text": "Malformed atom has no material flag.", "risk_types": [],
                 "relations": [], "cited_evidence_ids": []},
            ],
            "source_identities": [{
                "evidence_id": "e1", "source_organization": "Vendor A",
                "basis_field": "publisher", "basis_kind": "publisher_statement",
                "basis_text": "Published by Vendor A",
            }],
        })

    monkeypatch.setattr("gpt_researcher.utils.llm.create_chat_completion", author)
    researcher = SimpleNamespace(
        query="fixture",
        cfg=SimpleNamespace(smart_llm_model="fixture", smart_llm_provider="fixture",
                            smart_token_limit=5000, llm_kwargs={}),
        add_costs=lambda value: None,
        research_plan=SimpleNamespace(requirements=(req(),)),
    )
    context = EvidenceContext(
        context="", evidences=[ev(content="A documentation describes widgets.")]
    )
    plan = await propose_claims(researcher, context, "layered")
    result = integrate_claims(context, plan, CUTOFF)
    assert plan.invalid_structured_claim_input_count == 1
    assert plan.invalid_claim_texts == ["Malformed atom has no material flag."]
    assert plan.invalid_source_identity_input_count == 1
    assert result.layered_output_summary["verified_fact"] == 1
    report = render_report(
        result,
        writer_draft=(
            "A documentation describes widgets. "
            "Malformed atom has no material flag. "
            "The surrounding comparison remains readable."
        ),
    )
    assert "Malformed atom has no material flag" not in report
    assert "surrounding comparison remains readable" in report
    assert report.count("UNRESOLVED") == 1
