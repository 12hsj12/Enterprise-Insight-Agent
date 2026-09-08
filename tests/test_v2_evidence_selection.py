import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.documents import Document
from langchain_community.document_transformers.embeddings_redundant_filter import (
    get_stateful_documents,
)

from gpt_researcher.context.compression import ContextCompressor
from gpt_researcher.enterprise import (
    EVIDENCE_SELECTION_LIMITATION_CODES,
    IntelligenceRequest,
    IntelligenceWorkflow,
    ResearchTaskCategory,
    ResearchTaskClassifier,
    evidence_policy_for,
)
from gpt_researcher.enterprise.trace import RunTrace
from gpt_researcher.evidence import Evidence, EvidenceContext
from gpt_researcher.evidence.models import RetrievalDiagnostic
from gpt_researcher.evidence.reliability import EvidenceReliabilityEvaluator
from gpt_researcher.prompts import PromptFamily
from gpt_researcher.skills.context_manager import ContextManager


def _stateful_doc(content, url, similarity):
    doc = get_stateful_documents([
        Document(page_content=content, metadata={"source": url})
    ])[0]
    doc.state["query_similarity_score"] = similarity
    return doc


def _compressor_for_policy(policy, docs, monkeypatch):
    compressor = ContextCompressor(
        documents=[{"raw_content": "small", "url": "https://ignored.example"}],
        embeddings=None,
        max_results=10,
        evidence_policy=policy,
    )
    retriever = SimpleNamespace(invoke=lambda *args, **kwargs: list(docs))
    monkeypatch.setattr(
        compressor,
        "_ContextCompressor__get_contextual_retriever",
        lambda: retriever,
    )
    return compressor


@pytest.mark.asyncio
async def test_v2_policy_weight_controls_scores_and_can_change_ranking(monkeypatch):
    docs = [
        _stateful_doc("web", "https://example.com/evidence", 0.90),
        _stateful_doc("official", "https://openai.com/evidence", 0.85),
    ]
    decision_policy = evidence_policy_for(
        ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION
    )
    factual_policy = evidence_policy_for(ResearchTaskCategory.FACTUAL_VERIFICATION)

    decision = await _compressor_for_policy(
        decision_policy, docs, monkeypatch
    ).async_get_context("query", max_results=2)
    factual = await _compressor_for_policy(
        factual_policy, docs, monkeypatch
    ).async_get_context("query", max_results=2)

    assert [e.content for e in decision.evidences] == ["web", "official"]
    assert [e.content for e in factual.evidences] == ["official", "web"]
    assert decision.retrieval_diagnostics[0].final_score == pytest.approx(0.876)
    assert factual.retrieval_diagnostics[0].final_score == pytest.approx(0.895)


@pytest.mark.asyncio
async def test_v2_weighted_selection_always_uses_semantic_filter_path(monkeypatch):
    eligible = _stateful_doc(
        "eligible web", "https://example.com/eligible", 0.80
    )
    calls = []
    compressor = ContextCompressor(
        documents=[
            {"raw_content": "tiny", "url": "https://example.com/eligible"},
            {"raw_content": "tiny", "url": "https://openai.com/ineligible"},
        ],
        embeddings=None,
        evidence_policy=evidence_policy_for(
            ResearchTaskCategory.FACTUAL_VERIFICATION
        ),
    )
    monkeypatch.setattr(
        compressor,
        "_ContextCompressor__get_contextual_retriever",
        lambda: SimpleNamespace(
            invoke=lambda *args, **kwargs: calls.append(args[0]) or [eligible]
        ),
    )

    result = await compressor.async_get_context("semantic query", max_results=5)

    assert calls == ["semantic query"]
    assert [e.url for e in result.evidences] == [
        "https://example.com/eligible"
    ]
    assert "https://openai.com/ineligible" not in result.context


@pytest.mark.asyncio
async def test_maximum_policy_weight_keeps_semantic_relevance_dominant(monkeypatch):
    docs = [
        _stateful_doc("relevant web", "https://example.com/relevant", 0.95),
        _stateful_doc("weaker official", "https://openai.com/weaker", 0.70),
    ]
    policy = evidence_policy_for(ResearchTaskCategory.FACTUAL_VERIFICATION)

    result = await _compressor_for_policy(
        policy, docs, monkeypatch
    ).async_get_context("query", max_results=2)

    assert result.evidences[0].content == "relevant web"
    assert result.retrieval_diagnostics[0].similarity_score == 0.95


@pytest.mark.asyncio
async def test_v2_reranking_fails_safely_without_similarity_score(monkeypatch):
    missing = get_stateful_documents([
        Document(
            page_content="missing",
            metadata={"source": "https://openai.com/missing"},
        )
    ])[0]
    compressor = _compressor_for_policy(
        evidence_policy_for(ResearchTaskCategory.FACTUAL_VERIFICATION),
        [missing],
        monkeypatch,
    )

    with pytest.raises(ValueError, match="query_similarity_score"):
        await compressor.async_get_context("query")


def test_policy_is_source_of_truth_and_conflicting_fixed_weight_fails():
    policy = evidence_policy_for(ResearchTaskCategory.COMPETITIVE_COMPARISON)

    compressor = ContextCompressor([], None, evidence_policy=policy)
    assert compressor.evidence_policy is policy
    assert compressor.source_reliability_weight == policy.authority_weight

    with pytest.raises(ValueError, match="conflicts with EvidencePolicy"):
        ContextCompressor(
            [],
            None,
            source_reliability_weight=0.20,
            evidence_policy=policy,
        )


@pytest.mark.asyncio
async def test_context_manager_passes_typed_policy_without_environment_mutation(
    monkeypatch,
):
    classification = ResearchTaskClassifier().classify(
        "Compare platform A versus platform B."
    )
    policy = evidence_policy_for(classification.category)
    captured = {}
    environment_before = dict(os.environ)
    evidence = Evidence(
        evidence_id="ev_one", sub_query="q", url="https://example.com", content="text"
    )
    diagnostic = RetrievalDiagnostic(
        evidence_id="ev_one",
        similarity_score=0.8,
        authority_score=0.6,
        final_score=0.78,
    )

    def compressor(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            source_reliability_weight=policy.authority_weight,
            similarity_threshold=0.42,
            async_get_context=AsyncMock(
                return_value=EvidenceContext(
                    context="text",
                    evidences=[evidence],
                    retrieval_diagnostics=[diagnostic],
                )
            ),
        )

    monkeypatch.setattr(
        "gpt_researcher.skills.context_manager.ContextCompressor", compressor
    )
    collected_diagnostics = []
    researcher = SimpleNamespace(
        verbose=False,
        cfg=SimpleNamespace(source_reliability_weight=0.20, similarity_threshold=0.42),
        memory=SimpleNamespace(get_embeddings=lambda: None),
        prompt_family=PromptFamily,
        kwargs={"source_reliability_weight": 0.19},
        task_classification=classification,
        evidence_policy=policy,
        add_costs=lambda cost: None,
        add_evidences=lambda values: None,
        add_evidence_assessments=lambda values: None,
        add_retrieval_diagnostics=collected_diagnostics.extend,
    )

    trace = RunTrace("context-policy")
    with trace.activate():
        await ContextManager(researcher).get_similar_content_by_query("q", [])

    assert captured["evidence_policy"] is policy
    assert captured["source_reliability_weight"] is None
    assert collected_diagnostics == [diagnostic]
    assert dict(os.environ) == environment_before
    selection_event = next(
        event
        for event in trace.snapshot()["events"]
        if event["stage"] == "retrieval_selection"
    )
    assert selection_event["task_category"] == "competitive_comparison"
    assert selection_event["policy_version"] == policy.policy_version
    assert selection_event["authority_weight"] == policy.authority_weight
    assert selection_event["scores"] == [diagnostic.model_dump()]
    assert selection_event["corroboration_rule"] == policy.corroboration_rule
    assert selection_event["primary_source_rule"] == policy.primary_source_rule
    assert (
        selection_event["independent_source_rule"]
        == policy.independent_source_rule
    )
    assert selection_event["policy_limitation_codes"] == list(
        EVIDENCE_SELECTION_LIMITATION_CODES
    )


class _WorkflowResearcher:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.instances.append(self)
        self.evidence = Evidence(
            evidence_id="ev_fixture",
            sub_query=kwargs["query"],
            url="https://example.com/source",
            content="Fixture content",
        )

    async def conduct_research(self):
        return None

    async def write_report(self, custom_prompt):
        return "Fixture [claim](https://example.com/source)."

    def get_evidences(self):
        return [self.evidence]

    def get_evidence_assessments(self):
        return [EvidenceReliabilityEvaluator().evaluate(self.evidence)]

    def get_retrieval_diagnostics(self):
        return [RetrievalDiagnostic(
            evidence_id=self.evidence.evidence_id,
            similarity_score=0.8,
            authority_score=0.6,
            final_score=0.75,
        )]

    def get_costs(self):
        return 0.0


@pytest.mark.asyncio
async def test_v2_disabled_preserves_existing_workflow_behavior():
    _WorkflowResearcher.instances.clear()
    result = await IntelligenceWorkflow(_WorkflowResearcher).run(
        IntelligenceRequest(target="FixtureCo")
    )

    researcher = _WorkflowResearcher.instances[-1]
    assert "task_classification" not in researcher.kwargs
    assert "evidence_policy" not in researcher.kwargs
    assert result.task_classification is None
    assert result.evidence_policy is None
    assert result.evidence_selection_limitation_codes == []


@pytest.mark.parametrize(
    ("topic", "category"),
    [
        ("Verify whether the API is available.", ResearchTaskCategory.FACTUAL_VERIFICATION),
        ("Analyze the technical architecture.", ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS),
        ("Compare A versus B.", ResearchTaskCategory.COMPETITIVE_COMPARISON),
        ("Analyze the market adoption trend.", ResearchTaskCategory.TREND_MARKET_INTELLIGENCE),
        ("Resolve contradictory vendor claims.", ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION),
        ("Recommend which platform we should choose.", ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION),
    ],
)
@pytest.mark.asyncio
async def test_workflow_propagates_exact_policy_for_all_categories(topic, category):
    _WorkflowResearcher.instances.clear()
    result = await IntelligenceWorkflow(_WorkflowResearcher).run(
        IntelligenceRequest(
            target="FixtureCo",
            topic=topic,
            enable_v2_evidence_selection=True,
        )
    )

    researcher = _WorkflowResearcher.instances[-1]
    assert result.task_classification.category is category
    assert result.evidence_policy is evidence_policy_for(category)
    assert researcher.kwargs["task_classification"] == result.task_classification
    assert researcher.kwargs["evidence_policy"] is result.evidence_policy
    assert result.evidence_policy.category is category
    assert result.evidence_policy.policy_version
    assert result.evidence_policy.authority_weight == evidence_policy_for(
        category
    ).authority_weight


@pytest.mark.asyncio
async def test_report_template_expansion_does_not_contaminate_classification():
    _WorkflowResearcher.instances.clear()
    request = IntelligenceRequest(
        target="FixtureCo",
        topic="Enterprise implications and considerations.",
        dimensions=[
            "Compare A versus B",
            "Analyze the market adoption trend",
            "Recommend which platform to choose",
        ],
        enable_v2_evidence_selection=True,
    )
    assert ResearchTaskClassifier().classify(
        request.research_query()
    ).category is ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION

    result = await IntelligenceWorkflow(_WorkflowResearcher).run(request)

    assert result.task_classification.category is ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS
    assert result.task_classification.fallback_used is True


@pytest.mark.asyncio
async def test_v2_diagnostics_are_auditable_and_content_free():
    _WorkflowResearcher.instances.clear()
    trace = RunTrace("v2-trace")
    result = await IntelligenceWorkflow(_WorkflowResearcher).run(
        IntelligenceRequest(
            target="FixtureCo",
            topic="Verify whether the service is available.",
            enable_v2_evidence_selection=True,
        ),
        trace=trace,
    )

    score = result.retrieval_diagnostics[0]
    assert score.similarity_score == 0.8
    assert score.authority_score == 0.6
    assert score.final_score == 0.75
    assert result.evidence_selection_limitation_codes == list(
        EVIDENCE_SELECTION_LIMITATION_CODES
    )
    task_event = result.diagnostics["events"][0]
    assert task_event["task_category"] == "factual_verification"
    assert task_event["classifier_version"]
    assert task_event["classifier_confidence"] > 0
    assert task_event["fallback_used"] is False
    assert task_event["policy_version"]
    assert task_event["authority_weight"] == 0.30
    assert task_event["freshness_mode"] == "contextual"
    assert task_event["policy_reason_codes"]
    serialized_event = json.dumps(task_event)
    assert "Fixture content" not in serialized_event
    assert "example.com" not in serialized_event


def test_classification_remains_deterministic_through_request_intent():
    request = IntelligenceRequest(
        target="FixtureCo",
        topic="Compare A versus B.",
        enable_v2_evidence_selection=True,
    )
    classifier = ResearchTaskClassifier()

    assert classifier.classify(request.research_intent()) == classifier.classify(
        request.research_intent()
    )
