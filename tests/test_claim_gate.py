import inspect

import pytest
from pydantic import ValidationError

from gpt_researcher.evidence import (
    Claim,
    ClaimEvidenceLink,
    ClaimEvidenceQualification,
    ClaimGate,
    ClaimGateContext,
    ClaimGateDecision,
    ClaimGateReasonCode,
    ClaimGateResult,
    ClaimRiskType,
    Evidence,
    EvidenceContext,
    EvidenceStrengthRule,
    RISK_MINIMUM_RULES,
)


FROZEN_STRENGTH_RULES = {
    "standard",
    "primary_or_two_independent",
    "two_independent",
    "primary_plus_independent",
    "conflict_sides_plus_adjudicator",
}

FROZEN_RISK_MAPPING = {
    ClaimRiskType.NUMERIC_VALUE: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
    ClaimRiskType.DATE_OR_TIME_WINDOW: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
    ClaimRiskType.RELEASE_STATUS_AVAILABILITY: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
    ClaimRiskType.COMPARATIVE_CLAIM: EvidenceStrengthRule.TWO_INDEPENDENT,
    ClaimRiskType.SUPERLATIVE_OR_RANKING: EvidenceStrengthRule.TWO_INDEPENDENT,
    ClaimRiskType.MARKET_METRIC: EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
    ClaimRiskType.BENCHMARK_OR_PERFORMANCE: EvidenceStrengthRule.PRIMARY_PLUS_INDEPENDENT,
    ClaimRiskType.CONFLICT_SENSITIVE_CLAIM: EvidenceStrengthRule.CONFLICT_SIDES_PLUS_ADJUDICATOR,
}


def claim(*risk_types: ClaimRiskType | str) -> Claim:
    return Claim(
        scope_id="batch-4",
        normalized_text="A factual assertion.",
        risk_types=risk_types,
    )


def evidence(evidence_id: str, url: str = "") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        sub_query="fixture",
        content="fixture evidence",
        url=url,
    )


def link(item: Claim, evidence_id: str, relation: str = "support") -> ClaimEvidenceLink:
    return ClaimEvidenceLink(
        claim_id=item.claim_id,
        evidence_id=evidence_id,
        relation=relation,
    )


def qualification(evidence_id: str, **kwargs) -> ClaimEvidenceQualification:
    return ClaimEvidenceQualification(evidence_id=evidence_id, **kwargs)


def evaluate(
    item: Claim,
    evidence_ids: tuple[str, ...] = (),
    *,
    links: list[ClaimEvidenceLink] | None = None,
    qualifications: list[ClaimEvidenceQualification] | None = None,
    context: ClaimGateContext | None = None,
    urls: dict[str, str] | None = None,
) -> ClaimGateResult:
    urls = urls or {}
    return ClaimGate().evaluate(
        item,
        [evidence(item_id, urls.get(item_id, "")) for item_id in evidence_ids],
        links if links is not None else [link(item, item_id) for item_id in evidence_ids],
        qualifications or [],
        context,
    )


def test_frozen_strength_enum_and_risk_mapping_are_exact():
    assert {rule.value for rule in EvidenceStrengthRule} == FROZEN_STRENGTH_RULES
    assert RISK_MINIMUM_RULES == FROZEN_RISK_MAPPING


def test_standard_one_support_emits_and_no_support_omits():
    item = claim()
    supported = evaluate(item, ("ev-1",))
    unsupported = evaluate(item)

    assert supported.decision is ClaimGateDecision.EMIT
    assert supported.required_rules == (EvidenceStrengthRule.STANDARD,)
    assert supported.satisfied_requirements == ("valid_support",)
    assert unsupported.decision is ClaimGateDecision.OMIT
    assert unsupported.unmet_requirements == ("valid_support",)


@pytest.mark.parametrize(
    ("qualifications", "expected"),
    [
        ([qualification("ev-1", is_primary_source=True)], ClaimGateDecision.EMIT),
        (
            [
                qualification("ev-1", independence_group_id="publisher-a"),
                qualification("ev-2", independence_group_id="publisher-b"),
            ],
            ClaimGateDecision.EMIT,
        ),
        (
            [
                qualification("ev-1", independence_group_id="publisher-a"),
                qualification("ev-2", independence_group_id="publisher-a"),
            ],
            ClaimGateDecision.OMIT,
        ),
        ([qualification("ev-1"), qualification("ev-2")], ClaimGateDecision.OMIT),
    ],
)
def test_primary_or_two_independent_requires_explicit_qualification(
    qualifications, expected
):
    item = claim(ClaimRiskType.NUMERIC_VALUE)
    result = evaluate(item, ("ev-1", "ev-2"), qualifications=qualifications)
    assert result.decision is expected


def test_two_independent_requires_two_explicit_distinct_groups():
    item = claim(ClaimRiskType.COMPARATIVE_CLAIM)
    two_groups = evaluate(
        item,
        ("ev-1", "ev-2"),
        qualifications=[
            qualification("ev-1", independence_group_id="a"),
            qualification("ev-2", independence_group_id="b"),
        ],
    )
    same_group = evaluate(
        item,
        ("ev-1", "ev-2"),
        qualifications=[
            qualification("ev-1", independence_group_id="a"),
            qualification("ev-2", independence_group_id="a"),
        ],
    )
    assert two_groups.decision is ClaimGateDecision.EMIT
    assert same_group.unmet_requirements == ("two_independent_support_groups",)


@pytest.mark.parametrize(
    ("qualifications", "expected"),
    [
        (
            [
                qualification("ev-1", is_primary_source=True, independence_group_id="a"),
                qualification("ev-2", independence_group_id="b"),
            ],
            ClaimGateDecision.EMIT,
        ),
        (
            [
                qualification("ev-1", is_primary_source=True, independence_group_id="a"),
                qualification("ev-2", independence_group_id="a"),
            ],
            ClaimGateDecision.OMIT,
        ),
        (
            [
                qualification("ev-1", is_primary_source=True),
                qualification("ev-2", independence_group_id="b"),
            ],
            ClaimGateDecision.OMIT,
        ),
    ],
)
def test_primary_plus_independent_requires_primary_group_and_different_group(
    qualifications, expected
):
    item = claim(ClaimRiskType.BENCHMARK_OR_PERFORMANCE)
    result = evaluate(item, ("ev-1", "ev-2"), qualifications=qualifications)
    assert result.decision is expected


def test_multi_risk_is_a_semantic_union_not_a_weakest_rule_shortcut():
    item = claim(
        ClaimRiskType.NUMERIC_VALUE,
        ClaimRiskType.BENCHMARK_OR_PERFORMANCE,
    )
    result = evaluate(
        item,
        ("ev-1", "ev-2"),
        qualifications=[
            qualification("ev-1", independence_group_id="a"),
            qualification("ev-2", independence_group_id="b"),
        ],
    )

    assert result.required_rules == (
        EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
        EvidenceStrengthRule.PRIMARY_PLUS_INDEPENDENT,
    )
    assert result.resolved_obligations.evidence_strength_rules == result.required_rules
    assert result.satisfied_requirements == (
        "primary_or_two_independent_support",
    )
    assert result.unmet_requirements == (
        "primary_plus_different_independence_group",
    )
    assert result.decision is ClaimGateDecision.OMIT


def test_required_unit_rule_strengthens_and_never_weakens_claim_minimum():
    numeric = claim(ClaimRiskType.NUMERIC_VALUE)
    primary_only = [qualification("ev-1", is_primary_source=True)]
    strengthened = evaluate(
        numeric,
        ("ev-1",),
        qualifications=primary_only,
        context=ClaimGateContext(required_unit_rule="two_independent"),
    )
    benchmark = claim(ClaimRiskType.BENCHMARK_OR_PERFORMANCE)
    not_weakened = evaluate(
        benchmark,
        ("ev-1",),
        qualifications=primary_only,
        context=ClaimGateContext(required_unit_rule="standard"),
    )

    assert strengthened.required_rules == (
        EvidenceStrengthRule.PRIMARY_OR_TWO_INDEPENDENT,
        EvidenceStrengthRule.TWO_INDEPENDENT,
    )
    assert "two_independent_support_groups" in strengthened.unmet_requirements
    assert not_weakened.required_rules == (
        EvidenceStrengthRule.PRIMARY_PLUS_INDEPENDENT,
        EvidenceStrengthRule.STANDARD,
    )
    assert "primary_plus_different_independence_group" in not_weakened.unmet_requirements


def test_direct_comparison_requires_base_independence_and_primary_per_entity():
    item = claim(ClaimRiskType.COMPARATIVE_CLAIM)
    context = ClaimGateContext(required_entity_ids=("product-a", "product-b"))
    qualifications = [
        qualification(
            "ev-a",
            independence_group_id="vendor-a",
            is_primary_source=True,
            supported_entity_ids=("product-a",),
        ),
        qualification(
            "ev-b",
            independence_group_id="vendor-b",
            is_primary_source=True,
            supported_entity_ids=("product-b",),
        ),
    ]
    complete = evaluate(
        item,
        ("ev-a", "ev-b"),
        qualifications=qualifications,
        context=context,
    )
    missing_entity = evaluate(
        item,
        ("ev-a", "ev-b"),
        qualifications=[qualifications[0], qualification("ev-b", independence_group_id="vendor-b")],
        context=context,
    )

    assert complete.decision is ClaimGateDecision.EMIT
    assert complete.satisfied_requirements[-2:] == (
        "comparable_primary:product-a",
        "comparable_primary:product-b",
    )
    assert missing_entity.unmet_requirements == ("comparable_primary:product-b",)


def test_conflict_requires_every_side_and_supporting_independent_adjudicator():
    item = claim(ClaimRiskType.CONFLICT_SENSITIVE_CLAIM)
    evidences = ("side-a", "side-b", "judge")
    links = [
        link(item, "side-a", "support"),
        link(item, "side-b", "conflict"),
        link(item, "judge", "support"),
    ]
    context = ClaimGateContext(required_material_side_ids=("vendor", "replication"))
    qualifications = [
        qualification("side-a", material_side_ids=("vendor",)),
        qualification("side-b", material_side_ids=("replication",)),
        qualification("judge", is_independent_adjudicator=True),
    ]
    result = evaluate(
        item,
        evidences,
        links=links,
        qualifications=qualifications,
        context=context,
    )

    assert result.decision is ClaimGateDecision.EMIT
    assert result.conflicting_evidence_ids == ("side-b",)
    assert result.satisfied_requirements == (
        "all_required_material_sides",
        "independent_adjudicating_support",
    )


def test_conflict_sides_without_adjudicator_hedges_but_missing_side_omits():
    item = claim(ClaimRiskType.CONFLICT_SENSITIVE_CLAIM)
    context = ClaimGateContext(required_material_side_ids=("a", "b"))
    sides = evaluate(
        item,
        ("ev-a", "ev-b"),
        links=[link(item, "ev-a"), link(item, "ev-b", "conflict")],
        qualifications=[
            qualification("ev-a", material_side_ids=("a",)),
            qualification("ev-b", material_side_ids=("b",)),
        ],
        context=context,
    )
    missing = evaluate(
        item,
        ("ev-a",),
        qualifications=[qualification("ev-a", material_side_ids=("a",))],
        context=context,
    )

    assert sides.decision is ClaimGateDecision.HEDGE
    assert sides.unmet_requirements == ("independent_adjudicating_support",)
    assert ClaimGateReasonCode.CONFLICT_UNADJUDICATED in sides.reason_codes
    assert missing.decision is ClaimGateDecision.OMIT
    assert "all_required_material_sides" in missing.unmet_requirements


def test_all_four_deterministic_decisions_are_reachable():
    ordinary = claim()
    emit = evaluate(ordinary, ("ev-1",))
    omit = evaluate(ordinary)
    retrieve_more = evaluate(
        ordinary,
        context=ClaimGateContext(allow_retrieve_more=True),
    )
    conflict = claim(ClaimRiskType.CONFLICT_SENSITIVE_CLAIM)
    hedge = evaluate(
        conflict,
        ("ev-a", "ev-b"),
        qualifications=[
            qualification("ev-a", material_side_ids=("a",)),
            qualification("ev-b", material_side_ids=("b",)),
        ],
        context=ClaimGateContext(required_material_side_ids=("a", "b")),
    )

    assert {emit.decision, omit.decision, retrieve_more.decision, hedge.decision} == set(
        ClaimGateDecision
    )


def test_urls_and_authority_like_source_labels_never_establish_independence_or_primary():
    item = claim(ClaimRiskType.NUMERIC_VALUE)
    result = evaluate(
        item,
        ("ev-1", "ev-2"),
        urls={"ev-1": "https://openai.com/a", "ev-2": "https://reuters.com/b"},
    )
    assert result.decision is ClaimGateDecision.OMIT
    assert result.unmet_requirements == ("primary_or_two_independent_support",)


def test_only_valid_explicit_links_count_and_unknown_ids_cannot_satisfy():
    item = claim()
    other = Claim(scope_id="batch-4", normalized_text="Another assertion.")
    result = evaluate(
        item,
        ("known",),
        links=[
            link(item, "known", "unclear"),
            ClaimEvidenceLink(claim_id=item.claim_id, evidence_id="unknown", relation="support"),
            ClaimEvidenceLink(claim_id=other.claim_id, evidence_id="known", relation="support"),
        ],
    )
    assert result.supporting_evidence_ids == ()
    assert result.decision is ClaimGateDecision.OMIT


def test_conflicting_qualification_records_are_rejected():
    item = claim()
    with pytest.raises(ValueError, match="Conflicting qualifications"):
        evaluate(
            item,
            ("ev-1",),
            qualifications=[
                qualification("ev-1", independence_group_id="a"),
                qualification("ev-1", independence_group_id="b"),
            ],
        )


def test_qualification_unknowns_are_explicit_and_models_forbid_extra_fields():
    value = qualification("ev-1")
    assert value.independence_group_id is None
    assert value.is_primary_source is None
    assert value.is_independent_adjudicator is None
    with pytest.raises(ValidationError):
        ClaimEvidenceQualification(evidence_id="ev-1", authority_score=1.0)


def test_gate_is_classifier_independent_and_has_no_authority_weight_input():
    public_inputs = set(inspect.signature(ClaimGate.evaluate).parameters)
    context_fields = set(ClaimGateContext.model_fields)
    qualification_fields = set(ClaimEvidenceQualification.model_fields)
    forbidden = {
        "category",
        "classification",
        "classifier_confidence",
        "authority_score",
        "authority_weight",
        "runner_up_categories",
    }
    assert not forbidden & public_inputs
    assert not forbidden & context_fields
    assert not forbidden & qualification_fields


def test_evidence_context_round_trips_typed_gate_artifacts():
    item = claim()
    ev = evidence("ev-1")
    q = qualification("ev-1", independence_group_id="publisher")
    result = ClaimGate().evaluate(item, [ev], [link(item, "ev-1")], [q])
    context = EvidenceContext(
        context="fixture",
        evidences=[ev],
        claims=[item],
        claim_evidence_links=[link(item, "ev-1")],
        claim_evidence_qualifications=[q],
        claim_gate_results=[result],
    )
    assert EvidenceContext.model_validate_json(context.model_dump_json()) == context
