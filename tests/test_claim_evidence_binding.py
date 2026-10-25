import hashlib
import json
import struct

import pytest
from pydantic import ValidationError

from gpt_researcher.evidence import (
    Claim,
    ClaimEvidenceBinder,
    ClaimEvidenceLink,
    ClaimRiskType,
    Evidence,
    EvidenceContext,
)
from gpt_researcher.evidence.models import normalize_claim_text, stable_claim_id


FROZEN_RISK_TYPES = {
    "numeric_value",
    "date_or_time_window",
    "release_status_availability",
    "comparative_claim",
    "superlative_or_ranking",
    "market_metric",
    "benchmark_or_performance",
    "conflict_sensitive_claim",
}


def claim(text="Revenue was $10 million.", **kwargs):
    return Claim(scope_id="run-1", normalized_text=text, **kwargs)


def evidence(evidence_id, url=""):
    return Evidence(
        evidence_id=evidence_id,
        sub_query="fixture",
        url=url,
        content="fixture evidence",
    )


def test_claim_id_is_deterministic_within_scope_and_normalized():
    first = claim("  Revenue\twas １０ million. ")
    second = claim("Revenue was 10 million.")

    assert first.normalized_text == "Revenue was 10 million."
    assert first.claim_id == second.claim_id
    assert first.claim_id == stable_claim_id("run-1", first.normalized_text)
    assert normalize_claim_text(" a\n b ") == "a b"


def test_claim_scope_is_part_of_identity():
    assert claim().claim_id != Claim(
        scope_id="run-2",
        normalized_text="Revenue was $10 million.",
    ).claim_id


def test_claim_id_length_prefix_eliminates_nul_delimiter_collision():
    first = Claim(scope_id="a\0b", normalized_text="c")
    second = Claim(scope_id="a", normalized_text="b\0c")

    assert first.claim_id != second.claim_id


def test_claim_id_is_deterministic_for_normalized_unicode_utf8_components():
    first = Claim(scope_id=" 研究\t范围 ", normalized_text="收入为 １０ 亿欧元。")
    second = Claim(scope_id="研究 范围", normalized_text="收入为 10 亿欧元。")

    assert first.scope_id == second.scope_id == "研究 范围"
    assert first.normalized_text == second.normalized_text == "收入为 10 亿欧元。"
    assert first.claim_id == second.claim_id
    assert first.claim_id == stable_claim_id(first.scope_id, first.normalized_text)
    scope_bytes = first.scope_id.encode("utf-8")
    text_bytes = first.normalized_text.encode("utf-8")
    expected_payload = (
        b"enterprise-insight-agent:claim-id:v2"
        + struct.pack(">Q", len(scope_bytes))
        + scope_bytes
        + struct.pack(">Q", len(text_bytes))
        + text_bytes
    )
    assert first.claim_id == f"claim_{hashlib.sha256(expected_payload).hexdigest()}"


def test_claim_rejects_identity_that_does_not_match_normalized_input():
    with pytest.raises(ValidationError, match="does not match"):
        Claim(
            claim_id="claim_wrong",
            scope_id="run-1",
            normalized_text="A factual assertion.",
        )


def test_claim_supports_zero_and_multiple_exact_frozen_risk_types():
    ordinary = claim("A factual assertion.")
    risky = claim(
        risk_types=[
            "numeric_value",
            ClaimRiskType.BENCHMARK_OR_PERFORMANCE,
            "numeric_value",
        ]
    )

    assert ordinary.risk_types == ()
    assert risky.risk_types == (
        ClaimRiskType.NUMERIC_VALUE,
        ClaimRiskType.BENCHMARK_OR_PERFORMANCE,
    )
    assert {item.value for item in ClaimRiskType} == FROZEN_RISK_TYPES


def test_claim_rejects_unknown_risk_type():
    with pytest.raises(ValidationError):
        claim(risk_types=["invented_risk"])


def test_claim_has_only_minimum_claim_semantics_and_no_classifier_dependency():
    fields = set(Claim.model_fields)
    assert fields == {
        "claim_id",
        "scope_id",
        "normalized_text",
        "risk_types",
        "is_material",
    }
    assert not {"category", "classification", "authority_score", "confidence"} & fields


def test_bind_one_claim_to_one_support_evidence():
    item = claim()
    binder = ClaimEvidenceBinder([item], [evidence("ev-1")])

    link = binder.bind(item.claim_id, "ev-1", "support")
    summary = binder.summarize([link])[0]

    assert link.claim_id == item.claim_id
    assert link.claim == item.normalized_text
    assert summary.supporting_evidence_ids == ("ev-1",)
    assert summary.has_valid_support is True


def test_multiple_support_links_are_preserved_and_deterministically_ordered():
    item = claim()
    binder = ClaimEvidenceBinder(
        [item],
        [evidence("ev-2"), evidence("ev-1")],
    )
    links = binder.bind_many([
        ClaimEvidenceLink(claim_id=item.claim_id, evidence_id="ev-2", relation="support"),
        ClaimEvidenceLink(claim_id=item.claim_id, evidence_id="ev-1", relation="support"),
    ])

    assert [link.evidence_id for link in links] == ["ev-1", "ev-2"]
    assert binder.summarize(links)[0].supporting_evidence_ids == ("ev-1", "ev-2")


def test_support_conflict_and_unclear_are_preserved_simultaneously():
    item = claim()
    binder = ClaimEvidenceBinder(
        [item],
        [evidence("ev-support"), evidence("ev-conflict"), evidence("ev-unclear")],
    )
    links = [
        binder.bind(item.claim_id, "ev-support", "support"),
        binder.bind(item.claim_id, "ev-conflict", "conflict"),
        binder.bind(item.claim_id, "ev-unclear", "unclear"),
    ]

    summary = binder.summarize(links)[0]
    assert summary.supporting_evidence_ids == ("ev-support",)
    assert summary.conflicting_evidence_ids == ("ev-conflict",)
    assert summary.unclear_evidence_ids == ("ev-unclear",)
    assert summary.publisher_independence_verified is False
    assert summary.limitation_codes == (
        "publisher_independence_metadata_unavailable",
    )


def test_unknown_claim_and_evidence_are_rejected():
    item = claim()
    binder = ClaimEvidenceBinder([item], [evidence("ev-1")])

    with pytest.raises(ValueError, match="Unknown claim_id"):
        binder.bind("claim_unknown", "ev-1", "support")
    with pytest.raises(ValueError, match="Unknown evidence_id"):
        binder.bind(item.claim_id, "ev-unknown", "support")


def test_exact_duplicate_links_are_deduplicated_but_distinct_relations_remain():
    item = claim()
    binder = ClaimEvidenceBinder([item], [evidence("ev-1")])
    support = ClaimEvidenceLink(
        claim_id=item.claim_id,
        evidence_id="ev-1",
        relation="support",
    )
    conflict = ClaimEvidenceLink(
        claim_id=item.claim_id,
        evidence_id="ev-1",
        relation="conflict",
    )

    links = binder.bind_many([support, support, conflict])

    assert [(link.evidence_id, link.relation) for link in links] == [
        ("ev-1", "support"),
        ("ev-1", "conflict"),
    ]


def test_summary_includes_registered_claim_without_links():
    item = claim()
    summary = ClaimEvidenceBinder([item], []).summarize([])[0]

    assert summary.claim_id == item.claim_id
    assert summary.has_valid_support is False
    assert summary.supporting_evidence_ids == ()


def test_legacy_claim_text_remains_compatible_but_claim_id_is_identity():
    link = ClaimEvidenceLink(
        claim="  legacy\tclaim ",
        evidence_id="ev-1",
        relation="support",
    )

    assert link.claim == "legacy claim"
    assert link.claim_id == stable_claim_id("legacy", "legacy claim")


def test_evidence_context_can_carry_batch3_objects_without_gate_decisions():
    item = claim()
    ev = evidence("ev-1")
    binder = ClaimEvidenceBinder([item], [ev])
    link = binder.bind(item.claim_id, ev.evidence_id, "support")
    context = EvidenceContext(
        context="fixture",
        evidences=[ev],
        claims=[item],
        claim_evidence_links=[link],
        claim_support_summaries=binder.summarize([link]),
    )

    restored = EvidenceContext.model_validate_json(context.model_dump_json())
    assert restored == context
    payload = json.loads(context.model_dump_json())
    assert not {"emit", "hedge", "omit", "retrieve_more"} & set(payload)


def test_evidence_model_has_no_claim_truth_or_confidence_fields():
    assert not {
        "claim_confidence",
        "truth_probability",
        "factual_correctness_probability",
    } & set(Evidence.model_fields)
