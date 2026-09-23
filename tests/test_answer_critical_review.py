import json
from datetime import date
from types import SimpleNamespace

import pytest

from gpt_researcher.enterprise.answer_critical import (
    AnswerCriticalAssignment,
    AnswerCriticalReason,
    AnswerCriticalReview,
    RecommendationPremiseReview,
    review_answer_critical_claims,
    validate_answer_critical_response,
)
from gpt_researcher.enterprise.integration import ClaimPlan, integrate_claims, render_report
from gpt_researcher.enterprise.requirements import ResearchRequirement, RequirementType
from gpt_researcher.enterprise.unit_audit import split_markdown_audit_units
from gpt_researcher.evidence.models import Evidence, EvidenceContext


CUTOFF = date(2026, 9, 5)


def requirement(requirement_id="R1", requirement_type=RequirementType.COMPARATIVE):
    return ResearchRequirement(
        requirement_id=requirement_id,
        text="Compare procurement-relevant capabilities",
        requirement_type=requirement_type,
        order=int(requirement_id[1:]),
        target_entities=("AWS", "Azure") if requirement_type is RequirementType.COMPARATIVE else (),
    )


def researcher():
    return SimpleNamespace(
        cfg=SimpleNamespace(
            smart_llm_model="fixture",
            smart_llm_provider="fixture",
            smart_token_limit=16000,
            llm_kwargs={},
        ),
        add_costs=lambda *args, **kwargs: None,
    )


def execution(draft, review, requirements=None):
    source = Evidence(
        evidence_id="ev_private_internal_identifier",
        sub_query="fixture",
        title="Vendor documentation",
        url="https://example.test/docs",
        content="The source supplies bounded comparison context.",
    )
    return integrate_claims(
        EvidenceContext(context="", evidences=[source]),
        ClaimPlan(
            items=[],
            requirements=requirements or [requirement()],
            answer_critical_review=review,
        ),
        CUTOFF,
    )


@pytest.mark.asyncio
async def test_one_batched_review_selects_locations_without_support_judgment():
    draft = (
        "## Summary\n\nAWS has a broad catalog. Background explains the market.\n\n"
        "## Decision\n\nChoose AWS if catalog breadth is decisive."
    )
    units = split_markdown_audit_units(draft)
    factual = next(unit for unit in units if "broad catalog" in unit.text)
    recommendation = next(unit for unit in units if unit.recommendation)
    calls = []

    async def completion(**kwargs):
        calls.append(kwargs)
        return json.dumps({
            "critical_units": [{
                "unit_id": factual.unit_id,
                "reasons": ["COMPARISON_DIFFERENTIATOR"],
                "requirement_ids": ["R1"],
            }],
            "recommendations": [{
                "unit_id": recommendation.unit_id,
                "premise_unit_ids": [factual.unit_id],
                "has_inline_factual_premise": False,
            }],
        })

    review = await review_answer_critical_claims(
        researcher(), units, [requirement()], completion=completion,
    )
    assert len(calls) == 1
    assert review.status == "complete"
    assert review.critical_unit_ids() == {factual.unit_id}
    assert review.mapped_requirement_ids() == {"R1"}
    assert not hasattr(review.assignments[0], "supported")


def test_incomplete_review_uses_bounded_location_fallback_not_all_prose():
    draft = (
        "Ordinary background remains useful.\n\n"
        "| Product | Capability |\n| --- | --- |\n| AWS | Managed service |\n\n"
        "Choose AWS if the capability fits."
    )
    units = split_markdown_audit_units(draft)
    review = validate_answer_critical_response(
        '{"critical_units":[],"recommendations":[]}', units, [requirement()],
    )
    ordinary = next(unit for unit in units if "Ordinary background" in unit.text)
    assert review.status == "fallback"
    assert ordinary.unit_id not in review.critical_unit_ids()
    assert review.missing_requirement_ids == ("R1",)
    assert review.missing_recommendation_unit_ids


def test_recommendation_cannot_use_another_recommendation_as_a_premise():
    draft = "Choose AWS. Choose Azure."
    units = split_markdown_audit_units(draft)
    response = json.dumps({
        "critical_units": [{
            "unit_id": units[0].unit_id,
            "reasons": ["EXECUTIVE_DECISION"],
            "requirement_ids": ["R1"],
        }],
        "recommendations": [
            {
                "unit_id": units[0].unit_id,
                "premise_unit_ids": [units[1].unit_id],
                "has_inline_factual_premise": False,
            },
            {
                "unit_id": units[1].unit_id,
                "premise_unit_ids": [],
                "has_inline_factual_premise": False,
            },
        ],
    })
    review = validate_answer_critical_response(response, units, [requirement()])
    assert review.status == "fallback"
    assert review.unknown_unit_count == 1


def test_only_answer_critical_claim_is_qualified_and_ordinary_high_risk_is_preserved():
    draft = (
        "## Comparison\n\nBedrock can host OpenAI models in addition to its catalog. "
        "The background notes a 2026 planning horizon."
    )
    units = split_markdown_audit_units(draft)
    critical = next(unit for unit in units if "host OpenAI" in unit.text)
    ordinary = next(unit for unit in units if "planning horizon" in unit.text)
    review = AnswerCriticalReview(
        status="complete",
        assignments=(AnswerCriticalAssignment(
            unit_id=critical.unit_id,
            reasons=(AnswerCriticalReason.PRODUCT_DECISION_FACT,),
            requirement_ids=("R1",),
        ),),
    )
    result = execution(draft, review)
    report = render_report(result, writer_draft=draft)
    assert "Current evidence does not establish" in report
    assert "Bedrock can host OpenAI models" in report
    assert "The background notes a 2026 planning horizon" in report
    ordinary_record = next(
        item for item in result.unit_audit_records if item.unit_id == ordinary.unit_id
    )
    assert ordinary_record.reason_codes == ("OUTSIDE_HIGH_RISK_GATE",)
    assert result.final_render_audit_summary["answer_critical_unsupported_strong_claims"] == 0
    assert result.final_render_audit_summary["answer_critical_mapped_requirement_count"] == 1


def test_recommendation_is_retained_and_made_conditional_without_self_premise():
    draft = "## Decision\n\nChoose AWS because it hosts every competitor model."
    unit = next(item for item in split_markdown_audit_units(draft) if item.recommendation)
    review = AnswerCriticalReview(
        status="complete",
        assignments=(AnswerCriticalAssignment(
            unit_id=unit.unit_id,
            reasons=(AnswerCriticalReason.RECOMMENDATION_PREMISE,),
            requirement_ids=("R1",),
        ),),
        recommendations=(RecommendationPremiseReview(
            unit_id=unit.unit_id,
            premise_unit_ids=(),
            has_inline_factual_premise=True,
        ),),
    )
    result = execution(draft, review)
    report = render_report(result, writer_draft=draft)
    assert "Choose AWS because it hosts every competitor model" in report
    assert "recommendation should be treated as conditional" in report
    assert result.final_render_audit_summary["recommendation_deletion_count"] == 0
    assert result.final_render_audit_summary["already_audited_premise_repeated_gate_count"] == 0


def test_adjacent_unsupported_claims_share_one_local_limitation_note():
    draft = "Acme hosts Model A. Acme hosts Model B. Background remains useful."
    units = split_markdown_audit_units(draft)
    critical = [unit for unit in units if "hosts Model" in unit.text]
    review = AnswerCriticalReview(
        status="complete",
        assignments=tuple(
            AnswerCriticalAssignment(
                unit_id=unit.unit_id,
                reasons=(AnswerCriticalReason.PRODUCT_DECISION_FACT,),
                requirement_ids=("R1",),
            )
            for unit in critical
        ),
    )
    report = render_report(execution(draft, review), writer_draft=draft)
    assert report.count("Current evidence does not establish") == 1
    assert "Acme hosts Model A" in report and "Acme hosts Model B" in report
    assert "Background remains useful" in report
