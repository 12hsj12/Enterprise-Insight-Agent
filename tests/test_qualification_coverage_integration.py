"""Deterministic qualification-coverage integration tests; no provider calls."""

from datetime import date
from types import SimpleNamespace

from gpt_researcher.context.compression import ContextCompressor
from gpt_researcher.enterprise.integration import (
    ClaimProposal,
    integrate_claims,
    register_proposal,
)
from gpt_researcher.evidence.gate import RISK_MINIMUM_RULES
from gpt_researcher.evidence.models import (
    ClaimRiskType,
    Evidence,
    EvidenceContext,
    EvidenceStrengthRule,
    GroundingStatus,
    RetrievalDiagnostic,
)


CUTOFF = date(2026, 9, 5)


def evidence(evidence_id, organization=None, owner=None, url=None, content=None):
    return Evidence(
        evidence_id=evidence_id,
        sub_query="fixture",
        title="Explicit fixture",
        url=url or f"https://example.invalid/{evidence_id}",
        content=content or "Published by Fixture Organization.",
        source_organization=organization,
        source_owner=owner,
    )


def proposal(
    relations,
    *,
    risks=(),
    entities=(),
    sides=(),
    source_identities=(),
):
    return ClaimProposal.model_validate({
        "source_identities": list(source_identities),
        "claims": [{
            "text": "A bounded factual claim.",
            "risk_types": list(risks),
            "is_material": True,
            "entity_references": [
                {"reference_id": reference, "name": name}
                for reference, name in entities
            ],
            "material_side_references": [
                {"reference_id": reference, "description": description}
                for reference, description in sides
            ],
            "relations": relations,
            "cited_evidence_ids": [item["evidence_id"] for item in relations],
        }],
    })


def support(evidence_id, **values):
    return {"evidence_id": evidence_id, "relation": "support", **values}


def execute(authored, evidences):
    plan = register_proposal(authored, "execution-one", evidences)
    return plan, integrate_claims(
        EvidenceContext(context="", evidences=evidences), plan, CUTOFF
    )


async def test_explicit_retrieval_metadata_reaches_evidence_without_url_inference():
    compressor = ContextCompressor(
        documents=[{
            "url": "https://unrelated-host.invalid/report",
            "title": "Report",
            "raw_content": "A" * 200,
            "publisher": "Publisher One",
            "source_owner": "Owner One",
            "author": "Author One",
            "publication_date": "2026-08-01",
        }],
        embeddings=None,
        source_reliability_weight=0,
        prompt_family=SimpleNamespace(pretty_print_docs=lambda docs, limit: "context"),
    )
    result = await compressor.async_get_context("query")
    selected = result.evidences[0]
    assert selected.publisher == "Publisher One"
    assert selected.source_owner == "Owner One"
    assert selected.author == "Author One"
    assert selected.publication_date == "2026-08-01"


def test_same_explicit_source_organization_has_same_independence_group():
    authored = proposal([support("a"), support("b")])
    plan = register_proposal(
        authored,
        "run",
        [evidence("a", organization="Publisher One"),
         evidence("b", organization="Publisher One")],
    )
    groups = [item.independence_group_id for item in plan.items[0].qualifications]
    assert len(groups) == 2 and groups[0] == groups[1]


def test_two_explicit_source_organizations_have_different_groups():
    authored = proposal([support("a"), support("b")])
    plan = register_proposal(
        authored,
        "run",
        [evidence("a", organization="Publisher One"),
         evidence("b", organization="Publisher Two")],
    )
    groups = {item.independence_group_id for item in plan.items[0].qualifications}
    assert None not in groups and len(groups) == 2


def test_url_or_domain_difference_alone_does_not_create_independence():
    plan = register_proposal(
        proposal([support("a"), support("b")]),
        "run",
        [evidence("a", url="https://one.example/a"),
         evidence("b", url="https://two.example/b")],
    )
    assert plan.items[0].qualifications == []
    assert all(item.status == "missing" for item in plan.source_identity_resolutions)


def test_authority_score_alone_does_not_create_primary_qualification():
    ev = evidence("a")
    authored = proposal(
        [support(
            "a",
            supported_entity_reference_ids=["entity-a"],
            primary_source_entity_reference_ids=["entity-a"],
        )],
        risks=[ClaimRiskType.NUMERIC_VALUE],
        entities=[("entity-a", "Entity A")],
    )
    plan = register_proposal(authored, "run", [ev])
    context = EvidenceContext(
        context="",
        evidences=[ev],
        retrieval_diagnostics=[RetrievalDiagnostic(
            evidence_id="a",
            similarity_score=0.9,
            authority_score=1.0,
            final_score=0.92,
        )],
    )
    execution = integrate_claims(context, plan, CUTOFF)
    qualification = plan.items[0].qualifications[0]
    assert qualification.is_primary_source is None
    assert execution.evidence_context.claim_gate_results[0].decision.value == "omit"


def test_explicit_first_party_source_identity_may_be_primary():
    authored = proposal(
        [support(
            "a",
            supported_entity_reference_ids=["entity-a"],
            primary_source_entity_reference_ids=["entity-a"],
        )],
        risks=[ClaimRiskType.NUMERIC_VALUE],
        entities=[("entity-a", "Entity A")],
    )
    plan, execution = execute(authored, [evidence("a", owner="Entity A")])
    qualification = plan.items[0].qualifications[0]
    assert qualification.is_primary_source is True
    assert qualification.supported_entity_ids
    assert execution.evidence_context.claim_gate_results[0].decision.value == "emit"


def test_missing_source_identity_remains_missing():
    authored = proposal([support(
        "a", supported_entity_reference_ids=["entity-a"]
    )], entities=[("entity-a", "Entity A")])
    plan = register_proposal(authored, "run", [evidence("a")])
    qualification = plan.items[0].qualifications[0]
    assert qualification.independence_group_id is None
    assert qualification.is_primary_source is None


def test_comparative_claim_populates_required_entities_and_partial_support_fails():
    authored = proposal(
        [support(
            "a",
            supported_entity_reference_ids=["entity-a"],
            primary_source_entity_reference_ids=["entity-a"],
        )],
        risks=[ClaimRiskType.COMPARATIVE_CLAIM],
        entities=[("entity-a", "Entity A"), ("entity-b", "Entity B")],
    )
    plan, execution = execute(authored, [evidence("a", owner="Entity A")])
    required = plan.items[0].gate_context.required_entity_ids
    assert len(required) == 2
    reference_map = {
        item.label: item.stable_id
        for item in plan.claim_reference_resolutions[0].entity_references
    }
    assert reference_map == {"Entity A": required[0], "Entity B": required[1]}
    assert plan.items[0].qualifications[0].supported_entity_ids == (required[0],)
    gate = execution.evidence_context.claim_gate_results[0]
    assert f"comparable_primary:{required[1]}" in gate.unmet_requirements
    assert gate.decision.value == "omit"


def test_primary_for_entity_a_does_not_bleed_into_supported_entity_b():
    authored = proposal(
        [support(
            "a",
            supported_entity_reference_ids=["entity-a", "entity-b"],
            primary_source_entity_reference_ids=["entity-a"],
        )],
        risks=[ClaimRiskType.COMPARATIVE_CLAIM],
        entities=[("entity-a", "Entity A"), ("entity-b", "Entity B")],
    )
    plan = register_proposal(authored, "run", [evidence("a", owner="Entity A")])
    assert plan.items[0].qualifications[0].is_primary_source is None


def test_conflict_claim_populates_sides_and_partial_side_mapping_fails():
    authored = proposal(
        [support("a", material_side_reference_ids=["side-a"])],
        risks=[ClaimRiskType.CONFLICT_SENSITIVE_CLAIM],
        sides=[("side-a", "Position A"), ("side-b", "Position B")],
    )
    plan, execution = execute(authored, [evidence("a", organization="Publisher")])
    required = plan.items[0].gate_context.required_material_side_ids
    assert len(required) == 2
    assert plan.items[0].qualifications[0].material_side_ids == (required[0],)
    gate = execution.evidence_context.claim_gate_results[0]
    assert "all_required_material_sides" in gate.unmet_requirements
    assert gate.decision.value == "omit"


def test_high_authority_third_party_is_not_automatic_adjudicator():
    authored = proposal(
        [support("a")],
        risks=[ClaimRiskType.CONFLICT_SENSITIVE_CLAIM],
        entities=[("entity-a", "Entity A"), ("entity-b", "Entity B")],
        sides=[("side-a", "Position A"), ("side-b", "Position B")],
    )
    ev = evidence("a", organization="High Authority Publisher")
    plan = register_proposal(authored, "run", [ev])
    assert plan.items[0].qualifications[0].is_independent_adjudicator is None


def test_anchored_source_identity_is_accepted_but_invalid_authoring_fails_closed():
    valid = {
        "evidence_id": "a",
        "source_organization": "Publisher One",
        "basis_field": "content",
        "basis_kind": "publisher_statement",
        "basis_text": "Published by Publisher One.",
    }
    authored = proposal([support("a")], source_identities=[valid])
    plan = register_proposal(authored, "run", [
        evidence("a", content="Report.\nPublished by Publisher One.\nEnd.")
    ])
    assert plan.items[0].qualifications[0].independence_group_id is not None

    invalid = dict(valid, source_organization="Invented Organization")
    failed = register_proposal(
        proposal([
            support("a", supported_entity_reference_ids=["unknown"])
        ], source_identities=[invalid]),
        "run",
        [evidence("a", content="Report.\nPublished by Publisher One.\nEnd.")],
    )
    assert failed.items[0].qualifications == []
    assert failed.dropped_qualification_input_count >= 2
    assert failed.source_identity_resolutions[0].status == "rejected_unverifiable_anchor"

    mere_mention = dict(
        valid,
        source_organization="Entity A",
        basis_kind="unverified",
        basis_text="Entity A says the product is available.",
    )
    mentioned = register_proposal(
        proposal([support("a")], source_identities=[mere_mention]),
        "run",
        [evidence("a", content="Entity A says the product is available.")],
    )
    assert mentioned.items[0].qualifications == []

    described_elsewhere = dict(
        valid,
        source_organization="Entity A",
        basis_text="A study published by Entity A.",
    )
    described = register_proposal(
        proposal([support("a")], source_identities=[described_elsewhere]),
        "run",
        [evidence("a", content="A study published by Entity A.")],
    )
    assert described.items[0].qualifications == []


def test_gate_and_grounding_contracts_remain_unchanged():
    assert RISK_MINIMUM_RULES == {
        ClaimRiskType.NUMERIC_VALUE: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
        ClaimRiskType.DATE_OR_TIME_WINDOW: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
        ClaimRiskType.RELEASE_STATUS_AVAILABILITY: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
        ClaimRiskType.COMPARATIVE_CLAIM: EvidenceStrengthRule.TWO_INDEPENDENT,
        ClaimRiskType.SUPERLATIVE_OR_RANKING: EvidenceStrengthRule.TWO_INDEPENDENT,
        ClaimRiskType.MARKET_METRIC: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
        ClaimRiskType.BENCHMARK_OR_PERFORMANCE: EvidenceStrengthRule.PRIMARY_PLUS_INDEPENDENT,
        ClaimRiskType.CONFLICT_SENSITIVE_CLAIM: EvidenceStrengthRule.CONFLICT_SIDES_PLUS_ADJUDICATOR,
    }
    _, execution = execute(proposal([support("a")]), [evidence("a")])
    assert execution.evidence_context.claim_gate_results[0].decision.value == "emit"
    assert all(
        result.status is GroundingStatus.PASS
        for result in execution.evidence_context.grounding_validation_results
    )
    diagnostics = execution.qualification_diagnostics
    assert diagnostics.qualification_available_count == 0
    assert diagnostics.qualification_missing_count == 1
