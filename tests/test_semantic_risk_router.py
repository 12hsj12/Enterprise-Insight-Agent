import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from gpt_researcher.enterprise.integration import ClaimPlan, integrate_claims, render_report
from gpt_researcher.enterprise.semantic_risk import (
    SEMANTIC_HIGH_RISK_CATEGORIES,
    SemanticRiskAssignment,
    SemanticRiskCategory,
    SemanticRiskRouting,
    route_semantic_risk,
    validate_semantic_risk_response,
)
from gpt_researcher.enterprise.unit_audit import split_markdown_audit_units
from gpt_researcher.evidence.models import Evidence, EvidenceContext


CUTOFF = date(2026, 9, 5)
CORPUS_PATH = Path(__file__).parent / "fixtures" / "semantic_risk_adversarial.json"


def _researcher():
    return SimpleNamespace(
        cfg=SimpleNamespace(
            smart_llm_model="fixture",
            smart_llm_provider="fixture",
            smart_token_limit=16000,
            llm_kwargs={},
        ),
        add_costs=lambda *args, **kwargs: None,
    )


def _execution(routing: SemanticRiskRouting):
    evidence = Evidence(
        evidence_id="one",
        sub_query="fixture",
        url="https://example.test/source",
        content="The source supplies general context.",
    )
    return integrate_claims(
        EvidenceContext(context="", evidences=[evidence]),
        ClaimPlan(items=[], semantic_risk_routing=routing),
        CUTOFF,
    )


@pytest.mark.asyncio
async def test_adversarial_semantic_corpus_has_zero_false_negatives_and_false_positives():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    units = []
    expected_by_text = {}
    for item in corpus:
        draft = item["text"]
        if item["shape"] == "bullet":
            draft = f"- {draft}"
        elif item["shape"] == "table":
            draft = f"| Dimension | Finding |\n| --- | --- |\n| Access | {draft} |"
        parsed = split_markdown_audit_units(draft)
        target = next(unit for unit in parsed if item["text"] in unit.text)
        units.append(target)
        expected_by_text[target.text] = item["category"]

    async def completion(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        return json.dumps({
            "routes": [{
                "unit_id": unit["unit_id"],
                "category": expected_by_text[unit["text"]],
            } for unit in payload["units"]],
        })

    routing = await route_semantic_risk(_researcher(), units, completion=completion)
    actual = routing.category_by_unit()
    expected_high_risk = {
        unit.unit_id for unit in units
        if SemanticRiskCategory(expected_by_text[unit.text]) in SEMANTIC_HIGH_RISK_CATEGORIES
    }
    ordinary = {unit.unit_id for unit in units} - expected_high_risk
    actual_high_risk = routing.semantic_high_risk_unit_ids()
    assert routing.status == "complete"
    assert expected_high_risk - actual_high_risk == set()  # semantic FN = 0
    assert actual_high_risk & ordinary == set()  # false positives = 0
    assert len(actual) == len(units)


def test_malformed_partial_duplicate_unknown_and_invalid_categories_fail_safe():
    units = split_markdown_audit_units(
        "Bedrock can host OpenAI models. Ordinary context remains useful."
    )
    first, second = units
    response = json.dumps({"routes": [
        {"unit_id": first.unit_id, "category": "OBJECTIVE_CAPABILITY"},
        {"unit_id": first.unit_id, "category": "ORDINARY_CONTEXT"},
        {"unit_id": "missing-unit", "category": "OBJECTIVE_CAPABILITY"},
        {"unit_id": second.unit_id, "category": "NOT_A_CATEGORY"},
    ]})
    routing = validate_semantic_risk_response(response, units)
    assert routing.status == "fallback"
    assert set(routing.fallback_audit_unit_ids) == {unit.unit_id for unit in units}
    assert set(routing.unrouted_unit_ids) == {unit.unit_id for unit in units}
    assert routing.duplicate_unit_count == 1
    assert routing.unknown_unit_count == 1
    assert routing.invalid_route_count == 1
    assert {"PARTIAL_OUTPUT", "DUPLICATE_UNIT", "UNKNOWN_UNIT", "INVALID_ROUTE"} <= set(
        routing.error_codes
    )


@pytest.mark.asyncio
async def test_provider_error_uses_deterministic_conservative_full_unit_fallback():
    units = split_markdown_audit_units(
        "## Findings\n\nThe comparison is useful. Bedrock can host OpenAI models."
    )

    async def broken_completion(**kwargs):
        raise RuntimeError("provider unavailable")

    routing = await route_semantic_risk(
        _researcher(), units, completion=broken_completion,
    )
    assert routing.status == "fallback"
    assert routing.provider_error_count == 1
    assert set(routing.fallback_audit_unit_ids) == {unit.unit_id for unit in units}


def test_semantic_high_risk_routes_detector_miss_into_existing_audit_without_deletion():
    draft = "## Capability\n\nBedrock can host OpenAI models. Context remains useful."
    units = split_markdown_audit_units(draft)
    target = next(unit for unit in units if "host OpenAI" in unit.text)
    assert not target.high_risk and not target.claim_bearing
    routing = SemanticRiskRouting(
        status="complete",
        assignments=[
            SemanticRiskAssignment(
                unit_id=unit.unit_id,
                category=(
                    SemanticRiskCategory.OBJECTIVE_CAPABILITY
                    if unit.unit_id == target.unit_id
                    else SemanticRiskCategory.ORDINARY_CONTEXT
                ),
            ) for unit in units
        ],
    )
    execution = _execution(routing)
    report = render_report(execution, writer_draft=draft)
    assert "Bedrock can host OpenAI models" in report
    assert "insufficient to verify the following conclusion" in report
    assert "Context remains useful" in report
    summary = execution.final_render_audit_summary
    assert summary["semantic_high_risk_units"] == 1
    assert summary["union_high_risk_units"] == 1
    assert summary["conservative_fallback_audit_units"] == 0
    assert summary["strict_audit_candidate_units"] == 1
    assert summary["audited_high_risk_units"] == 1
    assert summary["high_risk_bypass_units"] == 0
    assert summary["destructive_unit_deletion_count"] == 0
    assert summary["substring_fragment_deletion_count"] == 0


def test_semantic_router_cannot_downgrade_deterministic_high_risk():
    draft = "Acme guarantees a 99.99% SLA."
    unit = split_markdown_audit_units(draft)[0]
    assert unit.high_risk
    routing = SemanticRiskRouting(
        status="complete",
        assignments=[SemanticRiskAssignment(
            unit_id=unit.unit_id,
            category=SemanticRiskCategory.ORDINARY_CONTEXT,
        )],
    )
    execution = _execution(routing)
    report = render_report(execution, writer_draft=draft)
    assert "insufficient to verify" in report
    summary = execution.final_render_audit_summary
    assert summary["deterministic_high_risk_units"] == 1
    assert summary["semantic_high_risk_units"] == 0
    assert summary["union_high_risk_units"] == 1
    assert summary["conservative_fallback_audit_units"] == 0
    assert summary["strict_audit_candidate_units"] == 1
    assert summary["high_risk_bypass_units"] == 0


def test_semantic_fact_in_recommendation_is_qualified_without_losing_direction():
    draft = "## Decision\n\nChoose Bedrock because OpenAI models can be deployed there."
    unit = split_markdown_audit_units(draft)[0]
    assert unit.recommendation
    routing = SemanticRiskRouting(
        status="complete",
        assignments=[SemanticRiskAssignment(
            unit_id=unit.unit_id,
            category=SemanticRiskCategory.OBJECTIVE_CAPABILITY,
        )],
    )
    execution = _execution(routing)
    report = render_report(execution, writer_draft=draft)
    assert "Choose Bedrock because OpenAI models can be deployed there" in report
    assert "does not rely on any newly introduced objective detail" in report
    summary = execution.final_render_audit_summary
    assert summary["recommendation_new_high_risk_fact_count"] == 1
    assert summary["recommendation_new_high_risk_fact_qualified_count"] == 1
    assert summary["recommendation_deletion_count"] == 0
    assert summary["already_audited_premise_repeated_gate_count"] == 0
    assert summary["high_risk_bypass_units"] == 0


def test_coverage_denominator_cannot_hide_unrouted_candidates():
    draft = "Ordinary context. Bedrock can host OpenAI models."
    units = split_markdown_audit_units(draft)
    routing = validate_semantic_risk_response(
        json.dumps({"routes": [{
            "unit_id": units[0].unit_id,
            "category": "ORDINARY_CONTEXT",
        }]}),
        units,
    )
    execution = _execution(routing)
    render_report(execution, writer_draft=draft)
    summary = execution.final_render_audit_summary
    assert summary["total_content_units"] == 2
    assert summary["objective_candidate_units"] == 2
    assert summary["unrouted_candidate_units"] == 1
    assert summary["union_high_risk_units"] == 0
    assert summary["conservative_fallback_audit_units"] == 1
    assert summary["strict_audit_candidate_units"] == 1
    assert summary["audited_high_risk_units"] == 1
    assert summary["high_risk_bypass_units"] == 0
