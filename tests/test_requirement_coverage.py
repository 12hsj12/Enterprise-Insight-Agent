from datetime import date

import pytest

from gpt_researcher.enterprise.integration import (
    ClaimPlan,
    ClaimProposal,
    ClaimReferenceResolution,
    RegisteredClaimInput,
    StableReferenceResolution,
    _opaque_id,
    integrate_claims,
    register_proposal,
    render_report,
)
from gpt_researcher.enterprise.requirements import (
    RequirementCoverageStatus,
    RequirementType,
    ResearchRequirement,
)
from gpt_researcher.evidence.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimEvidenceQualification,
    ClaimGateContext,
    ClaimRiskType,
    Evidence,
    EvidenceContext,
)


CUTOFF = date(2026, 9, 5)


def evidence(eid):
    return Evidence(
        evidence_id=eid,
        sub_query="fixture",
        content="Structured fixture evidence.",
        url=f"https://example.org/{eid}",
    )


def requirement(rid, kind, text, entities=()):
    return ResearchRequirement(
        requirement_id=rid,
        text=text,
        requirement_type=kind,
        order=int(rid[1:]),
        target_entities=entities,
    )


def factual_item(rid, text, citations=("ev1",)):
    claim = Claim(scope_id="coverage", normalized_text=text)
    return RegisteredClaimInput(
        claim=claim,
        requirement_id=rid,
        links=[ClaimEvidenceLink(
            claim_id=claim.claim_id,
            evidence_id="ev1",
            relation="support",
        )],
        cited_evidence_ids=list(citations),
    )


def comparative_plan(requirement_entities, claim_entities, reference_entities=None):
    reference_entities = reference_entities or claim_entities
    claim = Claim(
        scope_id="coverage",
        normalized_text="Compare the supplied entities.",
        risk_types=(ClaimRiskType.COMPARATIVE_CLAIM,),
    )
    item = RegisteredClaimInput(
        claim=claim,
        requirement_id="R1",
        links=[
            ClaimEvidenceLink(claim_id=claim.claim_id, evidence_id=eid, relation="support")
            for eid in ("ev1", "ev2")
        ],
        qualifications=[
            ClaimEvidenceQualification(
                evidence_id=eid,
                independence_group_id=eid,
                is_primary_source=True,
                supported_entity_ids=tuple(
                    _opaque_id("entity", "coverage", entity)
                    for entity in claim_entities
                ),
            )
            for eid in ("ev1", "ev2")
        ],
        gate_context=ClaimGateContext(
            required_entity_ids=tuple(
                _opaque_id("entity", "coverage", entity)
                for entity in claim_entities
            )
        ),
        cited_evidence_ids=["ev1", "ev2"],
    )
    references = ClaimReferenceResolution(
        claim_id=claim.claim_id,
        entity_references=[
            StableReferenceResolution(
                writer_reference_id=f"entity-{index}",
                stable_id=_opaque_id("entity", "coverage", stable_entity),
                label=entity,
            )
            for index, (entity, stable_entity) in enumerate(
                zip(reference_entities, claim_entities), 1
            )
        ],
    )
    return ClaimPlan(
        requirements=[requirement(
            "R1", RequirementType.COMPARATIVE, "Compare A and B", requirement_entities
        )],
        items=[item],
        claim_reference_resolutions=[references],
    )


def test_comparative_requirement_rejects_wrong_entity_pair():
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[evidence("ev1"), evidence("ev2")]),
        comparative_plan(("A", "B"), ("C", "D")),
        CUTOFF,
    )
    assert execution.evidence_context.generated_claim_records
    assert execution.requirement_coverage[0].status is RequirementCoverageStatus.NOT_COVERED


def test_comparative_requirement_requires_all_target_entities_and_visible_section():
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[evidence("ev1"), evidence("ev2")]),
        comparative_plan(("Ａ", "B"), ("A", "B")),
        CUTOFF,
    )
    assert execution.requirement_coverage[0].status is RequirementCoverageStatus.COVERED
    assert "## Compare A and B" in render_report(execution)


def test_comparative_labels_cannot_disguise_different_stable_obligations():
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[evidence("ev1"), evidence("ev2")]),
        comparative_plan(("A", "B"), ("C", "D"), reference_entities=("A", "B")),
        CUTOFF,
    )
    assert execution.evidence_context.generated_claim_records
    assert execution.requirement_coverage[0].status is RequirementCoverageStatus.NOT_COVERED


def test_comparative_single_target_is_partial_coverage():
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[evidence("ev1"), evidence("ev2")]),
        comparative_plan(("A", "B"), ("A",)),
        CUTOFF,
    )
    assert execution.evidence_context.generated_claim_records
    assert execution.requirement_coverage[0].status is RequirementCoverageStatus.PARTIALLY_COVERED


def test_recommendation_requires_visible_supporting_requirement_content():
    requirements = [
        requirement("R1", RequirementType.FACTUAL, "Establish facts"),
        requirement("R2", RequirementType.RECOMMENDATION, "Recommend an option"),
    ]
    full = integrate_claims(
        EvidenceContext(context="", evidences=[evidence("ev1")]),
        ClaimPlan(
            requirements=requirements,
            items=[factual_item("R1", "Fact."), factual_item("R2", "Recommendation.")],
        ),
        CUTOFF,
    )
    assert [item.status for item in full.requirement_coverage] == [
        RequirementCoverageStatus.COVERED,
        RequirementCoverageStatus.COVERED,
    ]

    partial = integrate_claims(
        EvidenceContext(context="", evidences=[evidence("ev1")]),
        ClaimPlan(requirements=requirements, items=[factual_item("R2", "Recommendation.")]),
        CUTOFF,
    )
    assert partial.requirement_coverage[1].status is RequirementCoverageStatus.PARTIALLY_COVERED


def test_coverage_is_recomputed_after_repair_removes_claim():
    plan = ClaimPlan(
        requirements=[requirement("R1", RequirementType.FACTUAL, "Establish facts")],
        items=[factual_item("R1", "Fact without a final citation.", citations=())],
    )
    execution = integrate_claims(
        EvidenceContext(context="", evidences=[evidence("ev1")]), plan, CUTOFF
    )
    assert any(action.operation.value == "remove_claim" for action in execution.repair_plan.actions)
    assert execution.evidence_context.generated_claim_records == []
    assert execution.requirement_coverage[0].status is RequirementCoverageStatus.NOT_COVERED


def test_explicit_claim_plan_unknown_requirement_fails_closed():
    proposal = ClaimProposal.model_validate({
        "claims": [{
            "requirement_id": "R9",
            "text": "A claim.",
            "risk_types": [],
            "is_material": True,
            "relations": [],
            "cited_evidence_ids": [],
        }]
    })
    with pytest.raises(ValueError, match="unknown requirement"):
        register_proposal(
            proposal,
            "coverage",
            requirements=[requirement("R1", RequirementType.FACTUAL, "Facts")],
        )
