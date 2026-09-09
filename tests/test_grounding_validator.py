import inspect
from datetime import date

import pytest
from pydantic import ValidationError

from gpt_researcher.evidence import (
    Claim,
    ClaimEvidenceLink,
    ClaimEvidenceQualification,
    ClaimGate,
    ClaimGateContext,
    ClaimGateDecision,
    ClaimRiskType,
    Evidence,
    EvidenceContext,
    GeneratedClaimOutputMode,
    GeneratedClaimRecord,
    GroundingEvidenceAuditMetadata,
    GroundingFindingCode,
    GroundingRepairOperation,
    GroundingStatus,
    GroundingValidator,
)


CUTOFF = date(2026, 9, 5)


def claim(text: str = "A factual assertion.", *risk_types) -> Claim:
    return Claim(
        scope_id="batch-5",
        normalized_text=text,
        risk_types=risk_types,
    )


def evidence(evidence_id: str) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        sub_query="fixture",
        content="fixture evidence",
    )


def link(item: Claim, evidence_id: str, relation: str = "support"):
    return ClaimEvidenceLink(
        claim_id=item.claim_id,
        evidence_id=evidence_id,
        relation=relation,
    )


def qualification(evidence_id: str, **kwargs):
    return ClaimEvidenceQualification(evidence_id=evidence_id, **kwargs)


def metadata(evidence_id: str, published: date | None = date(2026, 9, 1)):
    return GroundingEvidenceAuditMetadata(
        evidence_id=evidence_id,
        publication_date=published,
    )


def record(item: Claim, *citations: str, mode="factual"):
    return GeneratedClaimRecord(
        claim_id=item.claim_id,
        rendered_text=item.normalized_text,
        cited_evidence_ids=citations,
        output_mode=mode,
    )


def validate(
    records,
    *,
    claims,
    evidences,
    links,
    gate_results,
    qualifications=(),
    gate_contexts=None,
    audit_metadata=(),
    repair_attempt=0,
    validator=None,
):
    return (validator or GroundingValidator()).validate(
        records,
        claims=claims,
        evidences=evidences,
        links=links,
        gate_results=gate_results,
        qualifications=qualifications,
        gate_contexts=gate_contexts,
        audit_metadata=audit_metadata,
        cutoff_date=CUTOFF,
        repair_attempt=repair_attempt,
    )


def gate(item, evidences, links, qualifications=(), context=None):
    return ClaimGate().evaluate(
        item, evidences, links, qualifications, context
    )


def test_emit_with_sufficient_cited_support_passes():
    item = claim()
    ev = evidence("ev-1")
    links = [link(item, ev.evidence_id)]
    approved = gate(item, [ev], links)

    result = validate(
        [record(item, "ev-1")],
        claims=[item],
        evidences=[ev],
        links=links,
        gate_results=[approved],
        audit_metadata=[metadata("ev-1")],
    )

    assert approved.decision is ClaimGateDecision.EMIT
    assert result.status is GroundingStatus.PASS
    assert result.validated_claim_ids == (item.claim_id,)
    assert result.findings == ()


def test_emit_dropped_required_citation_reapplies_gate_and_requires_repair():
    item = claim("Product A outperforms Product B.", ClaimRiskType.COMPARATIVE_CLAIM)
    evidences = [evidence("ev-a"), evidence("ev-b")]
    links = [link(item, "ev-a"), link(item, "ev-b")]
    qualifications = [
        qualification("ev-a", independence_group_id="a"),
        qualification("ev-b", independence_group_id="b"),
    ]
    approved = gate(item, evidences, links, qualifications)

    result = validate(
        [record(item, "ev-a")],
        claims=[item],
        evidences=evidences,
        links=links,
        gate_results=[approved],
        qualifications=qualifications,
        audit_metadata=[metadata("ev-a"), metadata("ev-b")],
    )

    assert approved.decision is ClaimGateDecision.EMIT
    assert result.reapplied_gate_results[0].decision is ClaimGateDecision.OMIT
    assert result.status is GroundingStatus.REPAIR_REQUIRED
    assert GroundingFindingCode.INSUFFICIENT_FINAL_CITATIONS in result.reason_codes


@pytest.mark.parametrize(
    ("bad_id", "expected"),
    [
        ("unknown", GroundingFindingCode.UNKNOWN_CITATION),
        ("unlinked", GroundingFindingCode.CITATION_NOT_LINKED_TO_CLAIM),
    ],
)
def test_invalid_citation_is_reported_without_displacing_valid_support(
    bad_id, expected
):
    item = claim()
    evidences = [evidence("valid"), evidence("unlinked")]
    links = [link(item, "valid")]
    approved = gate(item, evidences, links)

    result = validate(
        [record(item, "valid", bad_id)],
        claims=[item],
        evidences=evidences,
        links=links,
        gate_results=[approved],
        audit_metadata=[metadata("valid"), metadata("unlinked")],
    )

    assert result.status is GroundingStatus.REPAIR_REQUIRED
    assert expected in result.reason_codes
    assert result.reapplied_gate_results[0].decision is ClaimGateDecision.EMIT


def conflict_fixture():
    item = claim("The reports conflict.", ClaimRiskType.CONFLICT_SENSITIVE_CLAIM)
    evidences = [evidence("side-a"), evidence("side-b")]
    links = [link(item, "side-a"), link(item, "side-b", "conflict")]
    qualifications = [
        qualification("side-a", material_side_ids=("a",)),
        qualification("side-b", material_side_ids=("b",)),
    ]
    context = ClaimGateContext(required_material_side_ids=("a", "b"))
    approved = gate(item, evidences, links, qualifications, context)
    return item, evidences, links, qualifications, context, approved


def test_hedge_required_with_explicit_hedged_mode_passes():
    item, evidences, links, qualifications, context, approved = conflict_fixture()
    result = validate(
        [record(item, "side-a", "side-b", mode="hedged")],
        claims=[item],
        evidences=evidences,
        links=links,
        gate_results=[approved],
        qualifications=qualifications,
        gate_contexts={item.claim_id: context},
        audit_metadata=[metadata("side-a"), metadata("side-b")],
    )
    assert approved.decision is ClaimGateDecision.HEDGE
    assert result.status is GroundingStatus.PASS
    assert result.reapplied_gate_results[0].conflicting_evidence_ids == ("side-b",)


def test_hedge_required_with_factual_mode_requires_repair():
    item, evidences, links, qualifications, context, approved = conflict_fixture()
    result = validate(
        [record(item, "side-a", "side-b")],
        claims=[item],
        evidences=evidences,
        links=links,
        gate_results=[approved],
        qualifications=qualifications,
        gate_contexts={item.claim_id: context},
        audit_metadata=[metadata("side-a"), metadata("side-b")],
    )
    assert result.status is GroundingStatus.REPAIR_REQUIRED
    assert result.reason_codes == (
        GroundingFindingCode.HEDGE_REQUIRED_BUT_UNQUALIFIED,
    )


@pytest.mark.parametrize(
    ("allow_retrieve_more", "expected_decision", "expected_code"),
    [
        (False, ClaimGateDecision.OMIT, GroundingFindingCode.OMITTED_CLAIM_EMITTED),
        (
            True,
            ClaimGateDecision.RETRIEVE_MORE,
            GroundingFindingCode.RETRIEVE_MORE_CLAIM_EMITTED,
        ),
    ],
)
def test_omit_and_retrieve_more_must_be_absent_but_emission_is_repairable(
    allow_retrieve_more, expected_decision, expected_code
):
    item = claim()
    context = ClaimGateContext(allow_retrieve_more=allow_retrieve_more)
    approved = gate(item, [], [], context=context)

    absent = validate(
        [], claims=[item], evidences=[], links=[], gate_results=[approved]
    )
    emitted = validate(
        [record(item)],
        claims=[item],
        evidences=[],
        links=[],
        gate_results=[approved],
        gate_contexts={item.claim_id: context},
    )

    assert approved.decision is expected_decision
    assert absent.status is GroundingStatus.PASS
    assert emitted.status is GroundingStatus.REPAIR_REQUIRED
    assert expected_code in emitted.reason_codes


def test_unknown_claim_is_a_repairable_identity_violation():
    emitted = GeneratedClaimRecord(
        claim_id="claim_unknown",
        rendered_text="Unknown assertion.",
    )
    result = validate(
        [emitted], claims=[], evidences=[], links=[], gate_results=[]
    )
    assert result.status is GroundingStatus.REPAIR_REQUIRED
    assert result.reason_codes == (GroundingFindingCode.UNKNOWN_CLAIM,)


def test_empty_rendered_text_is_rejected_by_the_typed_record_contract():
    with pytest.raises(ValidationError, match="rendered_text must not be empty"):
        GeneratedClaimRecord(claim_id="claim-1", rendered_text="  ")


def test_validator_calls_injected_claim_gate_with_only_cited_evidence():
    class SpyGate(ClaimGate):
        def __init__(self):
            self.evidence_ids = []

        def evaluate(self, claim, evidences, links, qualifications=(), context=None):
            evidence_list = list(evidences)
            self.evidence_ids.append(tuple(e.evidence_id for e in evidence_list))
            return super().evaluate(
                claim, evidence_list, links, qualifications, context
            )

    item = claim()
    evidences = [evidence("cited"), evidence("uncited")]
    links = [link(item, "cited"), link(item, "uncited")]
    approved = gate(item, evidences, links)
    spy = SpyGate()
    result = validate(
        [record(item, "cited")],
        claims=[item],
        evidences=evidences,
        links=links,
        gate_results=[approved],
        audit_metadata=[metadata("cited"), metadata("uncited")],
        validator=GroundingValidator(spy),
    )
    assert result.status is GroundingStatus.PASS
    assert spy.evidence_ids == [("cited",)]


def test_cutoff_metadata_pre_cutoff_passes_post_cutoff_blocks_and_absent_warns():
    item = claim()
    ev = evidence("ev-1")
    links = [link(item, "ev-1")]
    approved = gate(item, [ev], links)
    kwargs = dict(
        records=[record(item, "ev-1")],
        claims=[item],
        evidences=[ev],
        links=links,
        gate_results=[approved],
    )

    before = validate(audit_metadata=[metadata("ev-1")], **kwargs)
    after = validate(
        audit_metadata=[metadata("ev-1", date(2026, 9, 6))], **kwargs
    )
    absent = validate(**kwargs)

    assert before.status is GroundingStatus.PASS
    assert after.status is GroundingStatus.REPAIR_REQUIRED
    assert GroundingFindingCode.POST_CUTOFF_EVIDENCE in after.reason_codes
    assert after.reapplied_gate_results[0].decision is ClaimGateDecision.OMIT
    assert absent.status is GroundingStatus.PASS
    assert absent.reason_codes == (GroundingFindingCode.CUTOFF_UNVERIFIED,)
    assert absent.findings[0].blocking is False


def test_repair_plan_is_deterministic_and_applies_only_bounded_local_edits():
    item, evidences, links, qualifications, context, approved = conflict_fixture()
    extra = evidence("extra")
    records = [record(item, "side-a", "side-b", "unknown")]
    initial = validate(
        records,
        claims=[item],
        evidences=[*evidences, extra],
        links=links,
        gate_results=[approved],
        qualifications=qualifications,
        gate_contexts={item.claim_id: context},
        audit_metadata=[metadata("side-a"), metadata("side-b")],
    )

    first_plan = GroundingValidator.create_repair_plan(initial)
    second_plan = GroundingValidator.create_repair_plan(initial)
    repaired = GroundingValidator.apply_repair_plan(records, first_plan)

    assert first_plan == second_plan
    assert [action.operation for action in first_plan.actions] == [
        GroundingRepairOperation.MARK_CLAIM_HEDGED,
        GroundingRepairOperation.REMOVE_INVALID_CITATION,
    ]
    assert repaired[0].output_mode is GeneratedClaimOutputMode.HEDGED
    assert repaired[0].cited_evidence_ids == ("side-a", "side-b")
    assert set(repaired[0].cited_evidence_ids).issubset(records[0].cited_evidence_ids)


def test_repair_plan_removes_omit_claim_and_one_pass_is_terminal():
    item = claim()
    approved = gate(item, [], [])
    records = [record(item)]
    initial = validate(
        records, claims=[item], evidences=[], links=[], gate_results=[approved]
    )
    plan = GroundingValidator.create_repair_plan(initial)
    repaired = GroundingValidator.apply_repair_plan(records, plan)
    final = validate(
        repaired,
        claims=[item],
        evidences=[],
        links=[],
        gate_results=[approved],
        repair_attempt=1,
    )
    still_invalid = validate(
        records,
        claims=[item],
        evidences=[],
        links=[],
        gate_results=[approved],
        repair_attempt=1,
    )

    assert plan.actions[0].operation is GroundingRepairOperation.REMOVE_CLAIM
    assert repaired == []
    assert final.status is GroundingStatus.PASS
    assert final.repair_attempt == 1
    assert still_invalid.status is GroundingStatus.FAIL
    assert still_invalid.failed_claim_ids == (item.claim_id,)
    with pytest.raises(ValueError, match="No repair plan"):
        GroundingValidator.create_repair_plan(still_invalid)


def test_context_round_trip_and_public_models_are_classifier_independent():
    item = claim()
    emitted = record(item)
    validation = validate(
        [emitted], claims=[item], evidences=[], links=[], gate_results=[]
    )
    context = EvidenceContext(
        context="fixture",
        claims=[item],
        generated_claim_records=[emitted],
        grounding_validation_results=[validation],
    )
    restored = EvidenceContext.model_validate_json(context.model_dump_json())
    assert restored == context

    forbidden = {"category", "authority_weight", "classification"}
    assert not forbidden & set(GeneratedClaimRecord.model_fields)
    assert not forbidden & set(type(validation).model_fields)
    assert not forbidden & set(inspect.signature(GroundingValidator.validate).parameters)
