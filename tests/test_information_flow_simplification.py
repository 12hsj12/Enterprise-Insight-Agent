"""Offline boundaries for the restored Writer-first Enterprise V2 flow."""

import json
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
from gpt_researcher.enterprise.unit_audit import (
    AuditUnitState, AuditUnitType, is_high_risk, is_recommendation,
    split_markdown_audit_units,
)
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


def test_markdown_audit_units_have_stable_ids_types_and_original_positions():
    draft = (
        "# Comparison\n\nAcme supports private networking. Analysis remains useful.\n\n"
        "| Product | Price |\n| --- | --- |\n| Acme | $12/month |\n\n"
        "- Migrate to Acme only after a pilot.\n"
    )
    first = split_markdown_audit_units(draft)
    second = split_markdown_audit_units(draft)
    assert [unit.unit_id for unit in first] == [unit.unit_id for unit in second]
    assert {unit.unit_type for unit in first} >= {
        AuditUnitType.PROSE_SENTENCE,
        AuditUnitType.TABLE_CELL,
        AuditUnitType.LIST_ITEM,
    }
    for unit in first:
        assert draft[unit.start_offset:unit.end_offset] == unit.text
        assert unit.start_line >= 1 and unit.end_line >= unit.start_line


def test_sentence_units_protect_abbreviations_and_split_lowercase_product_names():
    draft = (
        "The U.S. Government publishes guidance. Teams should consult it. "
        "Multiple sources agree. pgvector is suitable below five million vectors."
    )
    units = split_markdown_audit_units(draft)
    assert [unit.text for unit in units] == [
        "The U.S. Government publishes guidance.",
        "Teams should consult it.",
        "Multiple sources agree.",
        "pgvector is suitable below five million vectors.",
    ]


def test_numbered_list_markers_and_citation_years_are_not_risk_facts():
    units = split_markdown_audit_units(
        "1. Prepare the migration discussion.\n"
        "2. Document the operating trade-off.\n\n"
        "The analysis remains useful ([Example, 2026](https://example.test/source))."
    )
    assert not any(unit.high_risk for unit in units)
    assert is_high_risk("Acme reports a 99.99% SLA in 2026.")
    assert is_high_risk("Acme supports private networking.")
    assert is_high_risk("Acme is faster because it uses a distributed index.")


@pytest.mark.parametrize("advice", [
    "The rate figures should be replaced with official vendor rate cards.",
    "Any benchmark figure should be reported with its checkpoint attached.",
    "Any benchmark figure should therefore be treated as a pointer.",
    "Bedrock is the better-supported choice.",
    "Migration becomes justified when volume exceeds ten million vectors.",
    "Milvus is the correct destination for large workloads.",
    "A firm with no DBA should collapse this to a single managed service.",
])
def test_confirmed_recommendation_forms_are_detected(advice):
    assert is_recommendation(advice)


@pytest.mark.parametrize("fact", [
    "Batch inference is 50% off on select models.",
    "50% off on select models",
])
def test_select_models_is_not_a_recommendation(fact):
    assert not is_recommendation(fact)


def test_decision_sections_promote_conditional_selection_candidates_only():
    draft = (
        "## Conclusion\n\n"
        "Where no operations capacity exists, Qdrant Cloud is the middle path. "
        "The evidence table remains available for review."
    )
    units = split_markdown_audit_units(draft)
    assert units[0].recommendation
    assert not units[1].recommendation


@pytest.mark.parametrize("leading_pipe", [True, False])
def test_table_cells_keep_exact_offsets_after_classifier_hardening(leading_pipe):
    if leading_pipe:
        draft = "| Product | Price |\n| --- | --- |\n| Acme | $12/month |"
    else:
        draft = "Product | Price\n--- | ---\nAcme | $12/month"
    first = split_markdown_audit_units(draft)
    second = split_markdown_audit_units(draft)
    assert [unit.unit_id for unit in first] == [unit.unit_id for unit in second]
    assert [unit.text for unit in first] == ["Product", "Price", "Acme", "$12/month"]
    assert all(draft[unit.start_offset:unit.end_offset] == unit.text for unit in first)
    assert not any(unit.high_risk for unit in first if unit.table_header)


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
    assert "当前证据强度有限" in report
    assert "LIMITED_EVIDENCE" not in report


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
    assert "AI_INFERENCE" not in report
    assert "consider pgvector" not in report
    assert execution.final_render_audit_summary[
        "recommendation_hidden_premise_suppressed_count"
    ] == 1


def test_unbound_high_risk_draft_fact_is_not_published():
    execution = integrate_claims(EvidenceContext(context="", evidences=[]),
                                 ClaimPlan(items=[]), CUTOFF)
    report = render_report(execution, writer_draft=(
        "## Market overview\n\nAcme captured 87% market share in 2026."
    ))
    assert "87%" not in report
    assert "当前可用证据不足" in report
    escaped = render_report(execution, writer_draft=(
        "## <script>alert(1)</script>\n\nAcme captured 87% market share in 2026."
    ))
    assert "<script>" not in escaped


def test_writer_draft_structure_and_analysis_survive_local_claim_audit():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Vendor documentation states that Acme traffic uses private endpoints.",
    )
    rejected = linked_claim(
        "Acme guarantees that traffic never traverses the public internet.",
        "R1", [source], risks=(ClaimRiskType.COMPARATIVE_CLAIM,),
    )
    draft = (
        "# Network comparison\n\n"
        "This section frames the decision around connectivity, operations, and risk.\n\n"
        "## Connectivity\n\n"
        "Acme guarantees that traffic never traverses the public internet. "
        "That distinction matters when teams compare deployment boundaries and controls.\n\n"
        "## Operating interpretation\n\n"
        + "The practical trade-off depends on the customer's control model and review process. " * 40
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(items=[rejected], requirements=[requirement(
            "R1", "网络对比", RequirementType.FACTUAL, 1
        )]), CUTOFF,
    )
    report = render_report(execution, writer_draft=draft)
    assert "# Network comparison" in report
    assert "## Connectivity" in report and "## Operating interpretation" in report
    assert "That distinction matters" in report
    assert "practical trade-off depends" in report
    assert "guarantees that traffic never traverses" not in report
    assert "Vendor documentation states" in report
    assert len(report) >= len(draft) * 0.8


def test_gate_reject_replaces_only_the_claim_not_its_paragraph():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Vendor documentation states that Acme supports private endpoints.",
    )
    rejected = linked_claim(
        "Acme is objectively safer than Beta.", "R1", [source],
        risks=(ClaimRiskType.COMPARATIVE_CLAIM,),
    )
    report = render_report(
        integrate_claims(
            EvidenceContext(context="", evidences=[source]),
            ClaimPlan(items=[rejected]), CUTOFF,
        ),
        writer_draft=(
            "## Comparison\n\nBefore choosing, define the relevant threat model. "
            "Acme is objectively safer than Beta. The comparison should also account "
            "for operational ownership and incident response."
        ),
    )
    assert "Before choosing" in report
    assert "operational ownership and incident response" in report
    assert "objectively safer" not in report
    assert "UNRESOLVED" not in report


def test_table_fact_failure_changes_only_its_cell_and_preserves_comparison():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Vendor documentation states that Acme traffic uses private endpoints.",
    )
    rejected = linked_claim(
        "Acme guarantees 99.99% SLA.", "R1", [source],
        risks=(ClaimRiskType.NUMERIC_VALUE,),
    )
    draft = (
        "## Service comparison\n\n"
        "| Product | SLA | Operating interpretation |\n"
        "| --- | --- | --- |\n"
        "| Acme | Acme guarantees 99.99% SLA. | Review incident ownership. |\n"
        "| Beta | Evidence varies by deployment. | Preserve the comparison boundary. |\n\n"
        "The table separates source claims from decision interpretation."
    )
    report = render_report(
        integrate_claims(
            EvidenceContext(context="", evidences=[source]),
            ClaimPlan(items=[rejected]), CUTOFF,
        ),
        writer_draft=draft,
    )
    assert "| Product | SLA | Operating interpretation |" in report
    assert "| Beta | — | Preserve the comparison boundary. |" in report
    assert "Review incident ownership" in report
    assert "separates source claims" in report
    assert "99.99%" not in report
    assert "| Acme | — |" in report
    assert "UNRESOLVED" not in report


def test_table_stronger_wording_runs_through_grounding_and_cannot_be_verified():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Vendor documentation states that Acme traffic uses private endpoints.",
    )
    claim = linked_claim(
        "Acme guarantees traffic never traverses the public internet.",
        "R1", [source], risks=(),
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[claim]), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "| Product | Network claim | Analysis |\n"
        "| --- | --- | --- |\n"
        "| Acme | Acme guarantees traffic never traverses the public internet. "
        "| Keep deployment assumptions explicit. |"
    ))
    assert execution.layered_output_summary["verified_fact"] == 0
    assert execution.layered_output_summary["limited_evidence"] == 1
    assert "guarantees traffic never" not in report
    assert "Vendor documentation states" in report
    assert "Keep deployment assumptions explicit" in report
    assert report.count("| --- | --- | --- |") == 1


def test_unaudited_table_price_is_scrubbed_without_deleting_row_or_table():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="The comparison uses a common decision frame.",
    )
    report = render_report(
        integrate_claims(EvidenceContext(context="", evidences=[source]),
                         ClaimPlan(items=[]), CUTOFF),
        writer_draft=(
            "Product | Price | Analysis\n"
            "--- | --- | ---\n"
            "Acme | $12 per month | Fits teams that value simplicity.\n"
            "Beta | Unknown | Requires a deployment-specific quote."
        ),
    )
    assert "$12" not in report
    assert "Acme |" in report and "Beta | — |" in report
    assert "Product | Price | Analysis" in report
    assert "Fits teams that value simplicity" in report
    assert "Acme | — |" in report
    assert "Requires a deployment-specific quote" in report


def test_unbound_draft_recommendation_is_removed_but_analysis_survives():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="The decision depends on the operating model.",
    )
    report = render_report(
        integrate_claims(EvidenceContext(context="", evidences=[source]),
                         ClaimPlan(items=[]), CUTOFF),
        writer_draft=(
            "## Decision\n\nThe trade-off depends on operational ownership. "
            "Choose pgvector for production. Preserve a reversible migration path."
        ),
    )
    assert "Choose pgvector" not in report
    assert "operational ownership" in report
    assert "reversible migration path" not in report
    assert "AI_INFERENCE" not in report


@pytest.mark.parametrize("advice", [
    "Teams should migrate to Milvus.",
    "We recommend pgvector.",
    "Milvus is the best choice for production.",
    "建议优先选择 pgvector。",
])
def test_selection_and_migration_advice_never_bypasses_premises(advice):
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="The decision depends on the operating model.",
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[]), CUTOFF,
    )
    report = render_report(
        execution,
        writer_draft=f"## Decision\n\n{advice} The operating-model trade-off remains.",
    )
    assert advice not in report
    assert "operating-model trade-off remains" in report
    assert execution.final_render_audit_summary[
        "unbound_recommendation_removed_count"
    ] == 1


def test_imperative_migration_list_items_are_removed_as_complete_units():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Migration requires workload-specific validation.",
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[]), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "## Migration\n\n"
        "1. Pin the embedding model version before migration.\n"
        "2. Run shadow reads against the new vector store.\n\n"
        "The sequence remains a workload-specific design exercise."
    ))
    assert "Pin the embedding model" not in report
    assert "Run shadow reads" not in report
    assert "workload-specific design exercise" in report
    assert execution.final_render_audit_summary["recommendation_bypass_count"] == 0
    assert execution.final_render_audit_summary["substring_fragment_deletion_count"] == 0


def test_high_risk_fact_adjacent_to_audited_placeholder_cannot_bypass_review():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Acme supports private endpoints.",
    )
    verified = linked_claim("Acme supports private endpoints", "R1", [source])
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[verified]), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "## Network\n\nAcme supports private endpoints and guarantees a 99.99% SLA in 2026. "
        "The comparison frame remains useful."
    ))
    assert "Acme supports private endpoints" in report
    assert "99.99%" not in report and "2026" not in report and "guarantees" not in report
    assert "comparison frame remains useful" in report
    assert any(
        record.state is AuditUnitState.LIMITED
        and "UNIT_COVERAGE_GAP_REMOVED_BY_WHOLE_UNIT_REWRITE" in record.reason_codes
        for record in execution.unit_audit_records
    )
    assert execution.final_render_audit_summary["substring_fragment_deletion_count"] == 0


def test_table_cell_adjacent_to_audited_placeholder_cannot_bypass_review():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Acme supports private endpoints.",
    )
    verified = linked_claim("Acme supports private endpoints", "R1", [source])
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[verified]), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "| Product | Network and price | Interpretation |\n"
        "| --- | --- | --- |\n"
        "| Acme | Acme supports private endpoints; price is $12/month | Keep scope explicit. |"
    ))
    assert "Acme supports private endpoints" in report
    assert "$12" not in report and "price is" not in report
    assert "Keep scope explicit" in report
    assert report.count("| --- | --- | --- |") == 1


def test_unaudited_benchmark_capability_and_causal_claims_are_removed_locally():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="The section uses a common comparison frame.",
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[]), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "## Findings\n\nAcme benchmark latency is 12 ms. "
        "Acme supports 1 million users. Because it uses Model X, it reduces cost by 40%. "
        "The section still explains how to compare operating boundaries."
    ))
    for unsafe in ("12 ms", "1 million", "Because it uses", "40%"):
        assert unsafe not in report
    assert "explains how to compare operating boundaries" in report
    assert execution.final_render_audit_summary[
        "unaudited_high_risk_unit_omitted_count"
    ] >= 3


def test_ordinary_factual_assertion_omitted_by_extractor_is_not_left_verbatim():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="The evidence uses a bounded comparison frame.",
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[]), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "## Business\n\nAcme builds widgets. "
        "The comparison separates facts from decision interpretation."
    ))
    assert "Acme builds widgets" not in report
    assert "separates facts from decision interpretation" in report
    assert execution.final_render_audit_summary[
        "unresolved_unit_count"
    ] == 1


def test_writer_recommendation_cannot_hide_in_factual_claim_array():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Choose Milvus for production.",
    )
    misclassified = linked_claim("Choose Milvus for production.", "R1", [source])
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(items=[misclassified]), CUTOFF,
    )
    assert execution.evidence_context.generated_claim_records
    report = render_report(
        execution,
        writer_draft="## Decision\n\nChoose Milvus for production. Keep the decision reversible.",
    )
    assert "Choose Milvus" not in report
    assert "decision reversible" in report
    assert execution.final_render_audit_summary[
        "unbound_recommendation_removed_count"
    ] == 1


def test_recommendation_is_suppressed_when_its_premise_is_not_visible_in_draft():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="pgvector offers HNSW indexing.",
    )
    hidden = linked_claim("pgvector offers HNSW indexing.", "R1", [source])
    inference = EvidenceGroundedInference(
        inference_id="hidden-premise", requirement_id="R2",
        text="Consider pgvector.", premise_claim_ids=(hidden.claim.claim_id,),
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(items=[hidden], inferences=[inference], requirements=[
            requirement("R1", "Capability", RequirementType.FACTUAL, 1),
            requirement("R2", "Recommendation", RequirementType.RECOMMENDATION, 2),
        ]), CUTOFF,
    )
    assert execution.surviving_inferences
    report = render_report(
        execution,
        writer_draft="## Decision\n\nThe decision depends on operational ownership.",
    )
    assert "Consider pgvector" not in report
    assert execution.final_render_audit_summary[
        "recommendation_hidden_premise_suppressed_count"
    ] == 1


def test_validated_recommendation_reenters_at_original_recommendation_unit():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="pgvector offers HNSW indexing.",
    )
    premise = linked_claim("pgvector offers HNSW indexing.", "R1", [source])
    inference = EvidenceGroundedInference(
        inference_id="bounded-pgvector", requirement_id="R2",
        text="Consider pgvector.", premise_claim_ids=(premise.claim.claim_id,),
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(items=[premise], inferences=[inference], requirements=[
            requirement("R1", "Capability", RequirementType.FACTUAL, 1),
            requirement("R2", "Recommendation", RequirementType.RECOMMENDATION, 2),
        ]), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "## Capability\n\npgvector offers HNSW indexing.\n\n"
        "## Decision\n\nChoose pgvector for production.\n\n"
        "The decision remains reversible."
    ))
    assert "Choose pgvector for production" not in report
    assert "Consider pgvector" in report
    assert report.index("Consider pgvector") < report.index("decision remains reversible")
    recommendation_records = [
        record for record in execution.unit_audit_records if record.recommendation
    ]
    assert len(recommendation_records) == 1
    assert recommendation_records[0].state is AuditUnitState.KEEP
    assert recommendation_records[0].inference_id == "bounded-pgvector"
    assert execution.final_render_audit_summary["recommendation_bypass_count"] == 0


@pytest.mark.parametrize("case_name", ["CC", "CR", "ED"])
def test_priority_case_writer_structure_and_explanation_are_preserved(case_name):
    source = Evidence(
        evidence_id="one", sub_query=case_name, url="https://example.test/one",
        content="The evidence uses a bounded comparison frame.",
    )
    explanation = (
        "The comparison separates source statements from operating interpretation and "
        "keeps deployment assumptions explicit. "
    )
    draft = (
        f"# {case_name} report\n\n## Evidence frame\n\n"
        + explanation * 20
        + "Acme reports a 99.99% SLA in 2026. "
        + "\n\n## Decision logic\n\n"
        + explanation * 10
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]), ClaimPlan(items=[]), CUTOFF,
    )
    report = render_report(execution, writer_draft=draft)
    assert f"# {case_name} report" in report
    assert "## Evidence frame" in report and "## Decision logic" in report
    assert report.count("keeps deployment assumptions explicit") == 30
    assert "99.99%" not in report and "2026" not in report
    assert len(report) >= len(draft) * 0.9
    assert not any(label in report for label in (
        "VERIFIED_FACT", "LIMITED_EVIDENCE", "UNRESOLVED", "AI_INFERENCE",
    ))


def test_malformed_atom_is_removed_locally_without_losing_surrounding_prose():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Acme builds widgets.",
    )
    valid = linked_claim("Acme builds widgets.", "R1", [source])
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(
            items=[valid], invalid_structured_claim_input_count=1,
            invalid_claim_texts=["Malformed atom states Beta has unlimited scale."],
        ), CUTOFF,
    )
    report = render_report(execution, writer_draft=(
        "## Capacity\n\nAcme builds widgets. The section keeps its comparison frame. "
        "Malformed atom states Beta has unlimited scale. "
        "Capacity still depends on the workload envelope."
    ))
    assert "Acme builds widgets" in report
    assert "VERIFIED_FACT" not in report
    assert "Malformed atom states" not in report
    assert "comparison frame" in report and "workload envelope" in report
    assert "UNRESOLVED" not in report


def test_approximately_29k_writer_draft_does_not_collapse_after_local_audit():
    source = Evidence(
        evidence_id="one", sub_query="fixture", url="https://example.test/one",
        content="Vendor documentation states that Acme uses private endpoints.",
    )
    rejected = linked_claim(
        "Acme guarantees that traffic never traverses the public internet.",
        "R1", [source], risks=(ClaimRiskType.COMPARATIVE_CLAIM,),
    )
    analysis = (
        "The comparison should preserve deployment context, operating ownership, "
        "and the distinction between source statements and decision interpretation. "
    )
    draft = (
        "# Complete comparison\n\n## Connectivity\n\n"
        "Acme guarantees that traffic never traverses the public internet. "
        + analysis * 210
        + "\n\n## Decision frame\n\n"
        + analysis * 20
    )
    assert 28_000 <= len(draft) <= 35_000
    report = render_report(
        integrate_claims(
            EvidenceContext(context="", evidences=[source]),
            ClaimPlan(items=[rejected]), CUTOFF,
        ), writer_draft=draft,
    )
    assert "# Complete comparison" in report and "## Decision frame" in report
    assert report.count("decision interpretation") == 230
    assert len(report) >= len(draft) * 0.95


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
    assert "Acme builds widgets" in result.report
    assert "VERIFIED_FACT" not in result.report
    assert Path(result.writer_draft_artifact_reference).read_text(encoding="utf-8")
    assert result.execution.writer_draft_sha256
    assert result.diagnostics["invalid_draft_claim_input_count"] == 0
    assert result.diagnostics["final_render_audit_summary"][
        "verified_claim_occurrence_count"
    ] == 1
    execution_artifact = json.loads(
        Path(result.execution_artifact_reference).read_text(encoding="utf-8")
    )
    assert execution_artifact["execution"]["final_render_audit_summary"] == (
        result.execution.final_render_audit_summary
    )
