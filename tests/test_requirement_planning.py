import json
from datetime import date
from types import SimpleNamespace

import pytest

from gpt_researcher.actions.query_processing import generate_sub_queries
from gpt_researcher.enterprise.requirements import RequirementType, ResearchPlan
from gpt_researcher.prompts import PromptFamily


def cfg():
    return SimpleNamespace(
        max_iterations=3,
        strategic_llm_model="fixture",
        strategic_llm_provider="fixture",
        strategic_token_limit=4000,
        smart_llm_model="fixture",
        smart_llm_provider="fixture",
        smart_token_limit=4000,
        temperature=0,
        llm_kwargs={},
    )


async def run_plan(monkeypatch, response, *, target="pgvector and Milvus", topic,
                   dimensions, calls=None):
    calls = calls if calls is not None else []

    async def provider(**kwargs):
        calls.append(kwargs["messages"][0]["content"])
        return response

    monkeypatch.setattr(
        "gpt_researcher.actions.query_processing.create_chat_completion",
        provider,
    )
    result = await generate_sub_queries(
        query=topic,
        parent_query="",
        report_type="research_report",
        context=[],
        cfg=cfg(),
        prompt_family=PromptFamily,
        requirement_context={
            "target": target,
            "topic": topic,
            "dimensions": dimensions,
            "cutoff_date": date(2026, 9, 5),
        },
    )
    assert isinstance(result, ResearchPlan)
    return result, calls


async def test_english_multidimensional_comparison_recommendation_and_constraints(monkeypatch):
    topic = (
        "Compare pgvector and Milvus on capabilities and operations, and recommend "
        "which a manufacturing company already using PostgreSQL should choose."
    )
    response = json.dumps({
        "requirements": [
            {"requirement_id": "R1", "text": "Compare capabilities.",
             "requirement_type": "COMPARATIVE", "order": 1,
             "constraints": ["manufacturing company", "already using PostgreSQL"],
             "target_entities": ["pgvector", "Milvus"],
             "source_dimensions": ["capabilities"]},
            {"requirement_id": "R2", "text": "Compare operations.",
             "requirement_type": "COMPARATIVE", "order": 2,
             "constraints": ["manufacturing company", "already using PostgreSQL"],
             "target_entities": ["pgvector", "Milvus"],
             "source_dimensions": ["operations"]},
            {"requirement_id": "R3", "text": "Recommend an option.",
             "requirement_type": "RECOMMENDATION", "order": 3,
             "constraints": ["manufacturing company", "already using PostgreSQL"],
             "target_entities": ["pgvector", "Milvus"], "source_dimensions": []},
        ],
        "sub_queries": [
            {"query": "pgvector Milvus capabilities", "requirement_ids": ["R1"]},
            {"query": "pgvector Milvus operations", "requirement_ids": ["R2"]},
            {"query": "pgvector Milvus manufacturing PostgreSQL choice",
             "requirement_ids": ["R1", "R2", "R3"]},
        ],
        "used_fallback": False,
        "fallback_reason": None,
    })
    plan, calls = await run_plan(
        monkeypatch, response, topic=topic, dimensions=["capabilities", "operations"]
    )
    assert [item.requirement_type for item in plan.requirements] == [
        RequirementType.COMPARATIVE,
        RequirementType.COMPARATIVE,
        RequirementType.RECOMMENDATION,
    ]
    assert plan.requirements[2].constraints == (
        "manufacturing company", "already using PostgreSQL"
    )
    assert len(calls) == 1
    assert "existing requirement IDs" in calls[0]


async def test_chinese_topic_and_dimensions_are_complementary(monkeypatch):
    topic = "从能力和运维比较 pgvector 与 Milvus，并为已使用 PostgreSQL 的制造企业给出选型建议。"
    response = json.dumps({
        "requirements": [
            {"requirement_id": "R1", "text": "比较两者的能力。",
             "requirement_type": "COMPARATIVE", "order": 1,
             "constraints": ["制造企业", "已使用 PostgreSQL"],
             "target_entities": ["pgvector", "Milvus"],
             "source_dimensions": ["能力"]},
            {"requirement_id": "R2", "text": "比较两者的运维。",
             "requirement_type": "COMPARATIVE", "order": 2,
             "constraints": ["制造企业", "已使用 PostgreSQL"],
             "target_entities": ["pgvector", "Milvus"],
             "source_dimensions": ["运维"]},
            {"requirement_id": "R3", "text": "给出选型建议。",
             "requirement_type": "RECOMMENDATION", "order": 3,
             "constraints": ["制造企业", "已使用 PostgreSQL"],
             "target_entities": ["pgvector", "Milvus"], "source_dimensions": []},
        ],
        "sub_queries": [
            {"query": "pgvector Milvus 能力比较", "requirement_ids": ["R1"]},
            {"query": "pgvector Milvus 运维比较", "requirement_ids": ["R2"]},
            {"query": "制造企业 PostgreSQL 向量库选型", "requirement_ids": ["R1", "R2", "R3"]},
        ],
        "used_fallback": False,
        "fallback_reason": None,
    }, ensure_ascii=False)
    plan, _ = await run_plan(
        monkeypatch, response, topic=topic, dimensions=["能力", "运维"]
    )
    assert len(plan.requirements) == 3
    assert plan.requirements[2].requirement_type is RequirementType.RECOMMENDATION
    assert [item.source_dimensions for item in plan.requirements[:2]] == [
        ("能力",), ("运维",)
    ]


async def test_topic_equal_to_explicit_dimension_stays_one_requirement(monkeypatch):
    response = json.dumps({
        "requirements": [{
            "requirement_id": "R1", "text": "Research security", "order": 1,
            "requirement_type": "FACTUAL", "constraints": [],
            "target_entities": ["Acme"], "source_dimensions": ["security"],
        }],
        "sub_queries": [{"query": "Acme security", "requirement_ids": ["R1"]}],
        "used_fallback": False, "fallback_reason": None,
    })
    plan, _ = await run_plan(
        monkeypatch, response, target="Acme", topic="security", dimensions=["security"]
    )
    assert not plan.used_fallback
    assert len(plan.requirements) == 1


async def test_more_than_five_explicit_dimensions_are_all_retained(monkeypatch):
    dimensions = [f"dimension-{index}" for index in range(1, 7)]
    response = json.dumps({
        "requirements": [
            {"requirement_id": f"R{index}", "text": f"Research {dimension}",
             "requirement_type": "FACTUAL", "order": index,
             "constraints": [], "target_entities": ["Acme"],
             "source_dimensions": [dimension]}
            for index, dimension in enumerate(dimensions, 1)
        ],
        "sub_queries": [
            {"query": dimension, "requirement_ids": [f"R{index}"]}
            for index, dimension in enumerate(dimensions, 1)
        ],
        "used_fallback": False,
        "fallback_reason": None,
    })
    plan, _ = await run_plan(
        monkeypatch, response, target="Acme", topic="Analyze Acme", dimensions=dimensions
    )
    assert len(plan.requirements) == 6
    assert {d for item in plan.requirements for d in item.source_dimensions} == set(dimensions)


@pytest.mark.parametrize("response", [
    "not valid JSON",
    json.dumps({
        "requirements": [{"requirement_id": "R1", "text": "General",
                          "requirement_type": "FACTUAL", "order": 1,
                          "constraints": [], "target_entities": [], "source_dimensions": []}],
        "sub_queries": [{"query": "general", "requirement_ids": ["R1"]}],
        "used_fallback": False, "fallback_reason": None,
    }),
    json.dumps({
        "requirements": [{"requirement_id": "R1", "text": "Security",
                          "requirement_type": "FACTUAL", "order": 1,
                          "constraints": [], "target_entities": [],
                          "source_dimensions": ["security"]}],
        "sub_queries": [{"query": "security", "requirement_ids": ["R9"]}],
        "used_fallback": False, "fallback_reason": None,
    }),
])
async def test_invalid_provider_plan_uses_lossless_fallback_without_another_call(monkeypatch, response):
    calls = []
    topic = "Compare options and recommend one"
    plan, calls = await run_plan(
        monkeypatch, response, target="A and B", topic=topic,
        dimensions=["security"], calls=calls,
    )
    assert plan.used_fallback
    assert len(calls) == 1
    assert any(item.source_dimensions == ("security",) for item in plan.requirements)
    assert any(item.text == topic for item in plan.requirements)


async def test_exact_structured_duplicate_is_rejected(monkeypatch):
    duplicate = {
        "requirement_type": "FACTUAL", "constraints": [],
        "target_entities": ["Acme"], "source_dimensions": ["security"],
    }
    response = json.dumps({
        "requirements": [
            {**duplicate, "requirement_id": "R1", "text": "Security", "order": 1},
            {**duplicate, "requirement_id": "R2", "text": "Analyze security", "order": 2},
        ],
        "sub_queries": [{"query": "security", "requirement_ids": ["R1", "R2"]}],
        "used_fallback": False, "fallback_reason": None,
    })
    plan, _ = await run_plan(
        monkeypatch, response, target="Acme", topic="Security", dimensions=["security"]
    )
    assert plan.used_fallback
