"""Batch 3 minimum-answer readiness and bounded retrieval effects."""

from datetime import date
import json
from types import SimpleNamespace

import pytest

from gpt_researcher.enterprise.integration import ClaimPlan
from gpt_researcher.enterprise.integration import RegisteredClaimInput
from gpt_researcher.enterprise.readiness import (
    RequirementAnswerReadinessReason,
    RequirementAnswerReadinessStatus,
    build_second_retrieval_queries,
    evaluate_requirement_readiness,
)
from gpt_researcher.enterprise.requirements import (
    PlannedSubQuery,
    RequirementType,
    ResearchPlan,
    ResearchRequirement,
)
from gpt_researcher.enterprise.task_policy import ResearchTaskCategory
from gpt_researcher.enterprise.trace import ResearchTraceRecorder
from gpt_researcher.enterprise.workflow import IntelligenceRequest, IntelligenceWorkflow
from gpt_researcher.evidence.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimGateContext,
    ClaimRiskType,
    Evidence,
    EvidenceMetadataProvenance,
    MetadataProvenanceKind,
)
from gpt_researcher.evidence.reliability import EvidenceReliabilityEvaluator
from gpt_researcher.skills.researcher import ResearchConductor


def requirement(
    rid: str,
    kind: RequirementType,
    text: str,
    *,
    order: int = 1,
    entities: tuple[str, ...] = (),
    dimensions: tuple[str, ...] = (),
    constraints: tuple[str, ...] = (),
) -> ResearchRequirement:
    return ResearchRequirement(
        requirement_id=rid,
        requirement_type=kind,
        text=text,
        order=order,
        target_entities=entities,
        source_dimensions=dimensions,
        constraints=constraints,
    )


def plan(*requirements: ResearchRequirement) -> ResearchPlan:
    return ResearchPlan(
        requirements=requirements,
        sub_queries=tuple(
            PlannedSubQuery(query=item.text, requirement_ids=(item.requirement_id,))
            for item in requirements
        ),
    )


def evidence(
    eid: str,
    query: str,
    content: str,
    *,
    url: str | None = None,
    dated: bool = False,
) -> Evidence:
    return Evidence(
        evidence_id=eid,
        sub_query=query,
        content=content,
        url=url or f"https://example.test/{eid}",
        publication_date="2026-09-01" if dated else None,
        metadata_provenance=EvidenceMetadataProvenance(
            publication_date=(
                MetadataProvenanceKind.HTML_STRUCTURED_METADATA
                if dated else MetadataProvenanceKind.UNKNOWN
            )
        ),
    )


def by_id(result):
    return {item.requirement_id: item for item in result}


def test_factual_one_direct_source_is_ready_and_zero_query():
    req = requirement("R1", RequirementType.FACTUAL, "Verify Acme availability")
    research_plan = plan(req)
    state = evaluate_requirement_readiness(
        research_plan, [evidence("ev1", req.text, "Acme is available.")]
    )

    assert state[0].status is RequirementAnswerReadinessStatus.READY
    assert build_second_retrieval_queries(research_plan, state)[0] == ()


def test_factual_without_support_needs_exactly_one_query():
    req = requirement("R1", RequirementType.FACTUAL, "Verify Acme availability")
    research_plan = plan(req)
    state = evaluate_requirement_readiness(research_plan, [])
    queries, exhausted = build_second_retrieval_queries(research_plan, state)

    assert state[0].reason is RequirementAnswerReadinessReason.NO_SUPPORTING_EVIDENCE
    assert [(item.requirement_id, item.query) for item in queries] == [
        ("R1", req.text)
    ]
    assert exhausted == ()


def test_comparison_both_sides_ready_without_independent_third_party():
    req = requirement(
        "R1", RequirementType.COMPARATIVE,
        "Compare pgvector and Milvus operational complexity",
        entities=("pgvector", "Milvus"),
    )
    research_plan = plan(req)
    state = evaluate_requirement_readiness(research_plan, [
        evidence("a", req.text, "Official pgvector deployment documentation."),
        evidence("b", req.text, "Official Milvus deployment documentation."),
    ])

    assert state[0].status is RequirementAnswerReadinessStatus.READY
    assert build_second_retrieval_queries(research_plan, state)[0] == ()


def test_comparison_missing_side_targets_only_that_side():
    req = requirement(
        "R1", RequirementType.COMPARATIVE,
        "Compare pgvector and Milvus operational complexity",
        entities=("pgvector", "Milvus"),
        dimensions=("operational complexity",),
        constraints=("deployment requirements",),
    )
    research_plan = plan(req)
    state = evaluate_requirement_readiness(
        research_plan,
        [evidence("a", req.text, "Official pgvector deployment documentation.")],
    )
    queries, _ = build_second_retrieval_queries(research_plan, state)

    assert state[0].missing_target_entities == ("Milvus",)
    assert queries[0].query == (
        "Milvus operational complexity deployment requirements"
    )
    assert "pgvector" not in queries[0].query.casefold()


def test_comparison_with_both_sides_missing_uses_one_requirement_query():
    req = requirement(
        "R1", RequirementType.COMPARATIVE, "Compare A and B capabilities",
        entities=("A", "B"),
    )
    research_plan = plan(req)
    state = evaluate_requirement_readiness(research_plan, [])
    queries, _ = build_second_retrieval_queries(research_plan, state)

    assert state[0].missing_target_entities == ("A", "B")
    assert [item.query for item in queries] == [req.text]


def test_recommendation_uses_fact_dependencies_and_never_queries_opinion():
    fact = requirement("R1", RequirementType.FACTUAL, "Acme capabilities")
    rec = requirement(
        "R2", RequirementType.RECOMMENDATION, "Recommend Acme", order=2
    )
    research_plan = plan(fact, rec)
    ready = evaluate_requirement_readiness(
        research_plan, [evidence("ev1", fact.text, "Acme capabilities are listed.")]
    )
    missing = evaluate_requirement_readiness(research_plan, [])
    queries, _ = build_second_retrieval_queries(research_plan, missing)

    assert by_id(ready)["R2"].status is RequirementAnswerReadinessStatus.READY
    assert by_id(missing)["R2"].reason is RequirementAnswerReadinessReason.DEPENDENCY_NOT_READY
    assert [(item.requirement_id, item.query) for item in queries] == [
        ("R1", fact.text)
    ]
    assert all("recommend" not in item.query.casefold() for item in queries)


def test_current_or_trend_requires_one_verifiable_date_only():
    req = requirement(
        "R1", RequirementType.FACTUAL, "What is Acme's current availability?"
    )
    research_plan = plan(req)
    undated = evaluate_requirement_readiness(
        research_plan, [evidence("old", req.text, "Acme is available.")]
    )
    dated = evaluate_requirement_readiness(
        research_plan, [evidence("new", req.text, "Acme is available.", dated=True)]
    )

    assert undated[0].reason is RequirementAnswerReadinessReason.NO_VERIFIABLE_TIME_CONTEXT
    assert dated[0].status is RequirementAnswerReadinessStatus.READY


def test_trend_task_does_not_make_stable_architecture_requirement_temporal():
    req = requirement(
        "R1",
        RequirementType.FACTUAL,
        "Describe Acme architecture",
        dimensions=("architecture",),
    )
    research_plan = plan(req)

    state = evaluate_requirement_readiness(
        research_plan,
        [evidence("architecture", req.text, "Acme architecture uses services.")],
        task_category=ResearchTaskCategory.TREND_MARKET_INTELLIGENCE,
    )

    assert state[0].status is RequirementAnswerReadinessStatus.READY


def test_recent_source_dimension_requires_verifiable_time_context():
    req = requirement(
        "R1",
        RequirementType.FACTUAL,
        "Summarize Acme developments",
        dimensions=("Recent developments",),
    )
    research_plan = plan(req)

    undated = evaluate_requirement_readiness(
        research_plan,
        [evidence("undated", req.text, "Acme announced a product development.")],
    )
    dated = evaluate_requirement_readiness(
        research_plan,
        [evidence(
            "dated",
            req.text,
            "Acme announced a product development.",
            dated=True,
        )],
    )

    assert undated[0].status is RequirementAnswerReadinessStatus.NEEDS_RETRIEVAL
    assert (
        undated[0].reason
        is RequirementAnswerReadinessReason.NO_VERIFIABLE_TIME_CONTEXT
    )
    assert dated[0].status is RequirementAnswerReadinessStatus.READY


def test_shared_query_evidence_only_supports_matching_structured_scope():
    architecture = requirement(
        "R1",
        RequirementType.FACTUAL,
        "Describe Acme architecture",
        dimensions=("architecture",),
    )
    price = requirement(
        "R2",
        RequirementType.FACTUAL,
        "Describe Acme price",
        order=2,
        dimensions=("price",),
    )
    shared_query = "Acme product overview"
    research_plan = ResearchPlan(
        requirements=(architecture, price),
        sub_queries=(PlannedSubQuery(
            query=shared_query,
            requirement_ids=("R1", "R2"),
        ),),
    )

    state = evaluate_requirement_readiness(
        research_plan,
        [evidence(
            "architecture",
            shared_query,
            "Acme architecture uses a service-oriented design.",
        )],
    )
    queries, _ = build_second_retrieval_queries(research_plan, state)

    assert by_id(state)["R1"].status is RequirementAnswerReadinessStatus.READY
    assert by_id(state)["R2"].status is RequirementAnswerReadinessStatus.NEEDS_RETRIEVAL
    assert [(item.requirement_id, item.query) for item in queries] == [
        ("R2", price.text)
    ]


def test_conflict_both_sides_ready_without_adjudicator_but_missing_side_retrieves():
    req = requirement(
        "R1", RequirementType.FACTUAL, "Resolve Alpha and Beta conflict",
        entities=("Alpha", "Beta"), dimensions=("conflicting claims",),
    )
    research_plan = plan(req)
    both = evaluate_requirement_readiness(
        research_plan,
        [
            evidence("a", req.text, "Alpha states X."),
            evidence("b", req.text, "Beta disputes X."),
        ],
        task_category=ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION,
    )
    one = evaluate_requirement_readiness(
        research_plan,
        [evidence("a", req.text, "Alpha states X.")],
        task_category=ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION,
    )
    queries, _ = build_second_retrieval_queries(research_plan, one)

    assert both[0].status is RequirementAnswerReadinessStatus.READY
    assert one[0].missing_target_entities == ("Beta",)
    assert queries[0].query.startswith("Beta ")


def test_six_missing_requirements_use_five_queries_and_record_sixth_exhausted():
    requirements = tuple(
        requirement(f"R{i}", RequirementType.FACTUAL, f"Fact {i}", order=i)
        for i in range(1, 7)
    )
    research_plan = plan(*requirements)
    state = evaluate_requirement_readiness(research_plan, [])
    queries, exhausted = build_second_retrieval_queries(research_plan, state)

    assert [item.requirement_id for item in queries] == [f"R{i}" for i in range(1, 6)]
    assert exhausted == ("R6",)


class _BoundedResearcher:
    instances = []
    initial: list[Evidence] = []
    recovered: list[Evidence] = []
    research_plan: ResearchPlan

    def __init__(self, **kwargs):
        self.query = kwargs["query"]
        self.requirement_planning_context = kwargs["requirement_planning_context"]
        self.research_plan = self.__class__.research_plan
        self.evidences = list(self.__class__.initial)
        self.targeted_calls = []
        self.__class__.instances.append(self)

    async def conduct_research(self):
        return None

    async def conduct_targeted_research(self, queries):
        self.targeted_calls.append(tuple(queries))
        self.evidences.extend(self.__class__.recovered)

    def get_evidences(self):
        return list(self.evidences)

    def get_evidence_assessments(self):
        return [EvidenceReliabilityEvaluator().evaluate(item) for item in self.evidences]

    def get_retrieval_diagnostics(self):
        return []

    def get_costs(self):
        return 0.0


@pytest.mark.asyncio
async def test_workflow_runs_only_one_second_round_and_persists_effect(tmp_path):
    req = requirement("R1", RequirementType.FACTUAL, "Verify Acme status")
    _BoundedResearcher.instances.clear()
    _BoundedResearcher.research_plan = plan(req)
    _BoundedResearcher.initial = []
    _BoundedResearcher.recovered = [evidence("new", req.text, "Acme is active.")]

    result = await IntelligenceWorkflow(
        _BoundedResearcher, output_directory=tmp_path
    ).run(
        IntelligenceRequest(
            target="Acme",
            topic="Verify Acme status",
            dimensions=["status"],
            enable_v2_execution=True,
            claim_plan=ClaimPlan(items=[], requirements=[req]),
        ),
        run_id="bounded",
    )
    researcher = _BoundedResearcher.instances[-1]
    artifact = json.loads(
        (tmp_path / "bounded" / "execution.json").read_text(encoding="utf-8")
    )

    assert researcher.targeted_calls == [(req.text,)]
    assert result.second_retrieval.triggered is True
    assert result.second_retrieval.queries_count == 1
    assert result.second_retrieval.readiness_after[0].status is RequirementAnswerReadinessStatus.READY
    assert artifact["second_retrieval"]["triggered"] is True
    assert artifact["second_retrieval"]["requirement_ids"] == ["R1"]
    assert result.execution.additional_retrieval_attempts == 0


@pytest.mark.asyncio
async def test_workflow_same_url_is_deduped_and_failure_does_not_trigger_third_round(tmp_path):
    req = requirement("R1", RequirementType.FACTUAL, "Verify Beta status")
    _BoundedResearcher.instances.clear()
    _BoundedResearcher.research_plan = plan(req)
    _BoundedResearcher.initial = [
        evidence("unmapped", "unmapped query", "Unrelated page.", url="https://x.test/p#old")
    ]
    _BoundedResearcher.recovered = [
        evidence("repeat", req.text, "Beta is active.", url="https://x.test/p")
    ]

    result = await IntelligenceWorkflow(
        _BoundedResearcher, output_directory=tmp_path
    ).run(
        IntelligenceRequest(
            target="Beta",
            topic="Verify Beta status",
            dimensions=["status"],
            enable_v2_execution=True,
            claim_plan=ClaimPlan(items=[], requirements=[req]),
        ),
        run_id="dedup",
        trace=ResearchTraceRecorder(run_id="dedup"),
    )

    assert _BoundedResearcher.instances[-1].targeted_calls == [(req.text,)]
    assert [item.evidence_id for item in result.evidences] == ["unmapped"]
    assert result.second_retrieval.readiness_after[0].status is RequirementAnswerReadinessStatus.NEEDS_RETRIEVAL
    second_event = next(
        item for item in result.diagnostics["events"]
        if item["stage"] == "second_retrieval"
    )
    assert second_event["second_retrieval_query_count"] == 1


@pytest.mark.asyncio
async def test_gate_retrieve_more_does_not_trigger_when_minimum_material_is_ready(tmp_path):
    req = requirement(
        "R1", RequirementType.COMPARATIVE, "Compare Alpha and Beta",
        entities=("Alpha", "Beta"),
    )
    alpha = evidence("alpha", req.text, "Alpha publishes capability A.")
    beta = evidence("beta", req.text, "Beta publishes capability B.")
    claim = Claim(
        scope_id="gate-decoupling",
        normalized_text="Alpha outperforms Beta.",
        risk_types=(ClaimRiskType.COMPARATIVE_CLAIM,),
    )
    claim_plan = ClaimPlan(
        requirements=[req],
        items=[RegisteredClaimInput(
            claim=claim,
            requirement_id="R1",
            links=[
                ClaimEvidenceLink(
                    claim_id=claim.claim_id, evidence_id="alpha", relation="support"
                ),
                ClaimEvidenceLink(
                    claim_id=claim.claim_id, evidence_id="beta", relation="support"
                ),
            ],
            gate_context=ClaimGateContext(allow_retrieve_more=True),
            cited_evidence_ids=["alpha", "beta"],
        )],
    )
    _BoundedResearcher.instances.clear()
    _BoundedResearcher.research_plan = plan(req)
    _BoundedResearcher.initial = [alpha, beta]
    _BoundedResearcher.recovered = []

    result = await IntelligenceWorkflow(
        _BoundedResearcher, output_directory=tmp_path
    ).run(
        IntelligenceRequest(
            target="Alpha and Beta",
            topic=req.text,
            dimensions=["comparison"],
            enable_v2_execution=True,
            claim_plan=claim_plan,
        ),
        run_id="gate-decoupling",
    )

    assert _BoundedResearcher.instances[-1].targeted_calls == []
    assert result.second_retrieval.queries_count == 0
    assert result.execution.evidence_context.claim_gate_results[0].decision.value == "retrieve_more"


@pytest.mark.asyncio
async def test_targeted_conductor_reuses_pipeline_once_without_mcp_planning():
    owner = SimpleNamespace(query_domains=[], context="initial")
    conductor = ResearchConductor(owner)
    calls = []

    async def process(query, scraped_data, domains, *, allow_mcp):
        calls.append((query, scraped_data, domains, allow_mcp))
        return f"context:{query}"

    conductor._process_sub_query = process
    result = await conductor.conduct_targeted_research(["q1", "q2"])

    assert result == ["context:q1", "context:q2"]
    assert calls == [
        ("q1", [], [], False),
        ("q2", [], [], False),
    ]
    assert owner.context == "initial\n\ncontext:q1\n\ncontext:q2"
