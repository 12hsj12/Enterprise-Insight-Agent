from gpt_researcher.evidence.models import Evidence
from gpt_researcher.evidence.consistency import EvidenceConsistencyEvaluator


def test_multiple_evidences_default_to_insufficient():
    evaluator = EvidenceConsistencyEvaluator()

    evidences = [
        Evidence(
            evidence_id="ev_1",
            sub_query="test",
            content="evidence one",
        ),
        Evidence(
            evidence_id="ev_2",
            sub_query="test",
            content="evidence two",
        ),
    ]

    assessment = evaluator.evaluate(evidences)

    assert assessment.evidence_ids == ["ev_1", "ev_2"]
    assert assessment.status == "insufficient"
    assert assessment.supporting_evidence_ids == []
    assert assessment.conflicting_evidence_ids == []


import pytest
from pydantic import ValidationError

from gpt_researcher.evidence.models import ClaimEvidenceLink


def test_claim_evidence_link_rejects_invalid_relation():
    with pytest.raises(ValidationError):
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_1",
            relation="invalid",
        )


def test_two_supporting_links_are_marked_supported():
    evaluator = EvidenceConsistencyEvaluator()

    evidences = [
        Evidence(
            evidence_id="ev_1",
            sub_query="test",
            url="https://source-a.com/article",
            content="evidence one",
        ),
        Evidence(
            evidence_id="ev_2",
            sub_query="test",
            url="https://source-b.com/article",
            content="evidence two",
        ),
    ]

    links = [
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_1",
            relation="support",
        ),
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_2",
            relation="support",
        ),
    ]

    assessment = evaluator.evaluate(evidences, links)

    assert assessment.status == "supported"
    assert assessment.supporting_evidence_ids == ["ev_1", "ev_2"]
    assert assessment.conflicting_evidence_ids == []


def test_conflicting_link_marks_assessment_as_conflict():
    evaluator = EvidenceConsistencyEvaluator()

    evidences = [
        Evidence(
            evidence_id="ev_1",
            sub_query="test",
            content="evidence one",
        ),
        Evidence(
            evidence_id="ev_2",
            sub_query="test",
            content="evidence two",
        ),
    ]

    links = [
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_1",
            relation="support",
        ),
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_2",
            relation="conflict",
        ),
    ]

    assessment = evaluator.evaluate(evidences, links)

    assert assessment.status == "conflict"
    assert assessment.supporting_evidence_ids == ["ev_1"]
    assert assessment.conflicting_evidence_ids == ["ev_2"]


def test_unknown_evidence_id_is_ignored():
    evaluator = EvidenceConsistencyEvaluator()

    evidences = [
        Evidence(
            evidence_id="ev_1",
            sub_query="test",
            content="evidence one",
        )
    ]

    links = [
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_999",
            relation="support",
        )
    ]

    assessment = evaluator.evaluate(evidences, links)

    assert assessment.status == "insufficient"
    assert assessment.supporting_evidence_ids == []
    assert assessment.conflicting_evidence_ids == []


def test_supporting_evidences_from_same_url_are_insufficient():
    evaluator = EvidenceConsistencyEvaluator()

    evidences = [
        Evidence(
            evidence_id="ev_1",
            sub_query="test",
            url="https://same-source.com/article",
            content="evidence one",
        ),
        Evidence(
            evidence_id="ev_2",
            sub_query="test",
            url="https://same-source.com/article",
            content="evidence two",
        ),
    ]

    links = [
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_1",
            relation="support",
        ),
        ClaimEvidenceLink(
            claim="test claim",
            evidence_id="ev_2",
            relation="support",
        ),
    ]

    assessment = evaluator.evaluate(evidences, links)

    assert assessment.status == "insufficient"