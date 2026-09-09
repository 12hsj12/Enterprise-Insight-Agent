import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from gpt_researcher.enterprise.task_policy import (
    CLASSIFIER_VERSION,
    POLICY_VERSION,
    EvidencePolicy,
    FreshnessMode,
    ResearchTaskCategory,
    ResearchTaskClassifier,
    TaskClassification,
    evidence_policy_for,
)


FROZEN_CATEGORIES = [
    "factual_verification",
    "technical_capability_analysis",
    "competitive_comparison",
    "trend_market_intelligence",
    "conflict_credibility_resolution",
    "enterprise_decision_recommendation",
]


def test_taxonomy_contains_exactly_the_six_frozen_serialized_values():
    assert [category.value for category in ResearchTaskCategory] == FROZEN_CATEGORIES


def test_task_classification_validates_and_serializes_the_typed_contract():
    classification = TaskClassification(
        category=ResearchTaskCategory.FACTUAL_VERIFICATION,
        confidence=1.0,
        classifier_version=CLASSIFIER_VERSION,
        matched_signal_codes=["explicit_verification"],
        runner_up_categories=[ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS],
        rationale_codes=["selected_narrow_fact_verification"],
        fallback_used=False,
    )

    serialized = classification.model_dump(mode="json")
    assert serialized["category"] == "factual_verification"
    assert serialized["confidence"] == 1.0
    assert serialized["runner_up_categories"] == ["technical_capability_analysis"]
    assert serialized["fallback_used"] is False


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_task_classification_accepts_confidence_bounds(confidence):
    classification = TaskClassification(
        category=ResearchTaskCategory.FACTUAL_VERIFICATION,
        confidence=confidence,
        classifier_version=CLASSIFIER_VERSION,
        matched_signal_codes=["explicit_verification"],
        runner_up_categories=[],
        rationale_codes=["selected_narrow_fact_verification"],
        fallback_used=False,
    )
    assert classification.confidence == confidence


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan")])
def test_task_classification_rejects_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        TaskClassification(
            category=ResearchTaskCategory.FACTUAL_VERIFICATION,
            confidence=confidence,
            classifier_version=CLASSIFIER_VERSION,
            matched_signal_codes=["explicit_verification"],
            runner_up_categories=[],
            rationale_codes=["selected_narrow_fact_verification"],
            fallback_used=False,
        )


def test_task_classification_rejects_invalid_runner_up_category():
    with pytest.raises(ValidationError):
        TaskClassification(
            category=ResearchTaskCategory.FACTUAL_VERIFICATION,
            confidence=0.8,
            classifier_version=CLASSIFIER_VERSION,
            matched_signal_codes=["explicit_verification"],
            runner_up_categories=["not_a_category"],
            rationale_codes=["selected_narrow_fact_verification"],
            fallback_used=True,
        )


@pytest.mark.parametrize(
    ("field", "invalid_code"),
    [
        ("matched_signal_codes", "I reasoned through hidden details"),
        ("rationale_codes", "because I privately inferred this"),
    ],
)
def test_task_classification_rejects_non_public_codes(field, invalid_code):
    values = {
        "category": ResearchTaskCategory.FACTUAL_VERIFICATION,
        "confidence": 0.8,
        "classifier_version": CLASSIFIER_VERSION,
        "matched_signal_codes": ["explicit_verification"],
        "runner_up_categories": [],
        "rationale_codes": ["selected_narrow_fact_verification"],
        "fallback_used": False,
    }
    values[field] = [invalid_code]

    with pytest.raises(ValidationError):
        TaskClassification(**values)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "核实该 API 是否默认保留客户数据。",
            ResearchTaskCategory.FACTUAL_VERIFICATION,
        ),
        (
            "分析向量索引的架构、机制与工程能力。",
            ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS,
        ),
        (
            "比较 AWS Bedrock 与 Azure OpenAI 的治理能力。",
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
        ),
        (
            "分析企业模型路由的市场采用趋势。",
            ResearchTaskCategory.TREND_MARKET_INTELLIGENCE,
        ),
        (
            "核查厂商声明与第三方复现结果的冲突和可信性。",
            ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION,
        ),
        (
            "为受监管企业选择部署方案并给出决策框架。",
            ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION,
        ),
    ],
)
def test_classifier_has_clear_examples_for_all_six_categories(query, expected):
    assert ResearchTaskClassifier().classify(query).category is expected


@pytest.mark.parametrize(
    ("query", "expected", "expected_runner_up"),
    [
        (
            "Recommend whether we should choose A versus B after resolving contradictory "
            "market trends and verifying their technical capabilities.",
            ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION,
            ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION,
        ),
        (
            "Resolve contradictory claims by comparing A versus B market trends and verify "
            "their technical capabilities.",
            ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION,
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
        ),
        (
            "Compare A versus B current market trends and verify their technical architecture.",
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
            ResearchTaskCategory.TREND_MARKET_INTELLIGENCE,
        ),
        (
            "Verify and analyze the market trend in API adoption over time.",
            ResearchTaskCategory.TREND_MARKET_INTELLIGENCE,
            ResearchTaskCategory.FACTUAL_VERIFICATION,
        ),
        (
            "Verify whether feature X is available and analyze its technical status.",
            ResearchTaskCategory.FACTUAL_VERIFICATION,
            ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS,
        ),
    ],
)
def test_classifier_applies_the_frozen_overlapping_intent_precedence(
    query,
    expected,
    expected_runner_up,
):
    result = ResearchTaskClassifier().classify(query)
    assert result.category is expected
    assert result.runner_up_categories[0] is expected_runner_up
    assert "frozen_precedence_applied" in result.rationale_codes


def test_classifier_falls_back_to_technical_for_an_unresolved_signal_tie():
    result = ResearchTaskClassifier().classify("Enterprise implications and considerations.")

    assert result.category is ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS
    assert result.confidence == 0.35
    assert result.matched_signal_codes == []
    assert result.runner_up_categories == []
    assert result.rationale_codes == [
        "no_explicit_task_signal",
        "fallback_unresolved_signal_tie",
    ]
    assert result.fallback_used is True


def test_classifier_is_deterministic_across_repeated_calls():
    classifier = ResearchTaskClassifier()
    query = "Compare two platforms and recommend which one an enterprise should adopt."

    assert classifier.classify(query) == classifier.classify(query)


@pytest.mark.parametrize(
    "query",
    [
        "分析数据库技术从单机架构向云原生架构演进的公开证据。",
        "研究企业软件平台由本地套件向托管服务转变的产业证据。",
        "分析数据基础设施从集中部署转向分布式平台的长期演进过程。",
        "近年来企业软件生态从单体套件走向模块化平台。",
        "研究检索技术正在向混合方法发展所体现的行业变化。",
        "Assess how the data-platform ecosystem evolved from warehouses to lakehouses.",
        "Study the industry technology transition from on-premise platforms to managed services.",
        "Analyze why retrieval technology adoption is shifting from dense-only search toward hybrid search.",
        "Examine how the enterprise AI ecosystem is moving toward governed agent workflows.",
    ],
)
# Direction alone no longer establishes historical scope; examples explicitly identify
# long-term, adoption, industry, ecosystem, or discipline development semantics.
def test_classifier_recognizes_temporal_process_evolution_without_trend_word(query):
    result = ResearchTaskClassifier().classify(query)

    assert result.category is ResearchTaskCategory.TREND_MARKET_INTELLIGENCE
    assert "temporal_process_evolution" in result.matched_signal_codes


@pytest.mark.parametrize(
    "query",
    [
        "Analyze how to move a file from folder A to folder B.",
        "Analyze how to copy data from system A to system B.",
        "Analyze how to convert format A to format B.",
        "Analyze how to migrate one configuration from cluster A to cluster B.",
        "分析如何将单个配置从集群 A 迁移到集群 B。",
    ],
)
def test_classifier_does_not_treat_generic_directional_operations_as_trends(query):
    result = ResearchTaskClassifier().classify(query)

    assert result.category is ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS
    assert "temporal_process_evolution" not in result.matched_signal_codes


@pytest.mark.parametrize(
    "query",
    [
        "核对官方与媒体说法是否一致，并解释分歧来源。",
        "评估许可证信息与官网描述是否一致。",
        "分析多方披露存在的差异及其可信性。",
        "Determine whether official and independent sources agree on the release status.",
        "Assess consistency across multiple authoritative reports about the incident.",
        "Explain differences between vendor documentation and independent reporting.",
    ],
)
def test_classifier_recognizes_multi_source_consistency_and_discrepancy(query):
    result = ResearchTaskClassifier().classify(query)

    assert result.category is ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION
    assert "source_account_consistency" in result.matched_signal_codes


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "Compare Product A and Product B on price and performance.",
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
        ),
        (
            "对比公司 A 和公司 B 的产品能力。",
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
        ),
        (
            "Verify whether Product X is available.",
            ResearchTaskCategory.FACTUAL_VERIFICATION,
        ),
        (
            "核实某产品是否已经发布。",
            ResearchTaskCategory.FACTUAL_VERIFICATION,
        ),
        (
            "Compare the numeric price difference between Product A and Product B.",
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
        ),
        (
            "比较产品 A 和产品 B 的数值性能差异。",
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
        ),
    ],
)
def test_classifier_does_not_confuse_entity_comparison_or_single_fact_with_source_conflict(
    query,
    expected,
):
    result = ResearchTaskClassifier().classify(query)

    assert result.category is expected
    assert "source_account_consistency" not in result.matched_signal_codes


@pytest.mark.parametrize(
    "query",
    [
        "What is the numeric difference between Product A and Product B prices?",
        "The performance discrepancy between Product A and Product B is five percent.",
        "产品 A 与产品 B 的性能数值差异是多少？",
    ],
)
def test_plain_entity_difference_is_not_credibility_resolution(query):
    result = ResearchTaskClassifier().classify(query)

    assert result.category is not ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION
    assert "source_account_consistency" not in result.matched_signal_codes


@pytest.mark.parametrize(
    ("query", "expected_runner_up"),
    [
        (
            "核查官方声明与独立报告是否一致。",
            ResearchTaskCategory.FACTUAL_VERIFICATION,
        ),
        (
            "Compare official and independent source accounts and explain their differences.",
            ResearchTaskCategory.COMPETITIVE_COMPARISON,
        ),
    ],
)
def test_source_consistency_signal_wins_by_frozen_precedence(query, expected_runner_up):
    result = ResearchTaskClassifier().classify(query)

    assert result.category is ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION
    assert result.runner_up_categories[0] is expected_runner_up
    assert "frozen_precedence_applied" in result.rationale_codes


def test_repaired_semantic_signals_remain_deterministic():
    classifier = ResearchTaskClassifier()
    query = "核查多个权威来源是否一致，并解释材料之间的差异。"

    results = [classifier.classify(query) for _ in range(10)]

    assert all(result == results[0] for result in results[1:])


def test_classifier_matches_all_frozen_dataset_categories_using_query_text_only():
    dataset_path = (
        Path(__file__).resolve().parents[1]
        / "benchmarks"
        / "dataset"
        / "enterprise_insight_bench_v2.json"
    )
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    classifier = ResearchTaskClassifier()
    results = [
        (
            case["id"],
            case["category"],
            classifier.classify(case["query"]).category.value,
        )
        for case in dataset["cases"]
    ]
    mismatches = [result for result in results if result[1] != result[2]]

    assert len(results) == 30
    assert not mismatches, f"frozen classifier mismatches: {mismatches}"


def test_classifier_accepts_only_query_text_not_benchmark_metadata():
    signature = inspect.signature(ResearchTaskClassifier.classify)
    assert list(signature.parameters) == ["self", "query"]
    with pytest.raises(TypeError):
        ResearchTaskClassifier().classify(
            "Analyze vector indexing internals.",
            case_id="EIV2_TC_001",
        )


EXPECTED_POLICIES = {
    ResearchTaskCategory.FACTUAL_VERIFICATION: {
        "authority_weight": 0.30,
        "preferred_source_types": (
            "official",
            "regulator_standard",
            "official_documentation",
            "authoritative_media",
        ),
        "freshness_mode": FreshnessMode.CONTEXTUAL,
        "max_age_days": 365,
        "corroboration_rule": "primary_or_two_independent",
        "primary_source_rule": "required_or_two_independent",
        "independent_source_rule": "publisher_organization",
    },
    ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS: {
        "authority_weight": 0.22,
        "preferred_source_types": (
            "official_documentation",
            "peer_reviewed_research",
            "regulator_standard",
            "independent_technical",
        ),
        "freshness_mode": FreshnessMode.CONTEXTUAL,
        "max_age_days": 730,
        "corroboration_rule": "primary_plus_independent",
        "primary_source_rule": "preferred",
        "independent_source_rule": "publisher_organization",
    },
    ResearchTaskCategory.COMPETITIVE_COMPARISON: {
        "authority_weight": 0.10,
        "preferred_source_types": (
            "official_documentation",
            "independent_technical",
            "authoritative_media",
            "peer_reviewed_research",
        ),
        "freshness_mode": FreshnessMode.STRICT,
        "max_age_days": 365,
        "corroboration_rule": "primary_plus_independent",
        "primary_source_rule": "one_per_compared_entity",
        "independent_source_rule": "publisher_organization",
    },
    ResearchTaskCategory.TREND_MARKET_INTELLIGENCE: {
        "authority_weight": 0.12,
        "preferred_source_types": (
            "regulator_standard",
            "authoritative_media",
            "industry_analysis",
            "official",
        ),
        "freshness_mode": FreshnessMode.STRICT,
        "max_age_days": 180,
        "corroboration_rule": "two_independent",
        "primary_source_rule": "preferred_for_measured_inputs",
        "independent_source_rule": "publisher_organization",
    },
    ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION: {
        "authority_weight": 0.18,
        "preferred_source_types": (
            "regulator_standard",
            "official_documentation",
            "peer_reviewed_research",
            "authoritative_media",
        ),
        "freshness_mode": FreshnessMode.CONTEXTUAL,
        "max_age_days": 365,
        "corroboration_rule": "conflict_sides_plus_adjudicator",
        "primary_source_rule": "source_for_each_material_side",
        "independent_source_rule": "publisher_organization",
    },
    ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION: {
        "authority_weight": 0.08,
        "preferred_source_types": (
            "official_documentation",
            "independent_technical",
            "industry_analysis",
            "peer_reviewed_research",
        ),
        "freshness_mode": FreshnessMode.CONTEXTUAL,
        "max_age_days": 730,
        "corroboration_rule": "two_independent",
        "primary_source_rule": "preferred",
        "independent_source_rule": "publisher_organization",
    },
}


@pytest.mark.parametrize("category", list(ResearchTaskCategory))
def test_each_category_has_the_exact_frozen_evidence_policy(category):
    policy = evidence_policy_for(category)
    expected = EXPECTED_POLICIES[category]

    assert policy.policy_version == POLICY_VERSION
    assert policy.category is category
    for field, value in expected.items():
        assert getattr(policy, field) == value
    assert policy.authority_weight <= 0.30
    assert policy.reason_codes


@pytest.mark.parametrize(
    ("query", "expected_category"),
    [
        ("Verify whether the service is available.", ResearchTaskCategory.FACTUAL_VERIFICATION),
        ("Analyze the component architecture.", ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS),
        ("Compare service A versus service B.", ResearchTaskCategory.COMPETITIVE_COMPARISON),
        ("Analyze the market adoption trend.", ResearchTaskCategory.TREND_MARKET_INTELLIGENCE),
        ("Resolve the contradictory vendor claims.", ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION),
        ("Recommend which platform we should choose.", ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION),
    ],
)
def test_policy_category_matches_the_classifier_category(query, expected_category):
    classification = ResearchTaskClassifier().classify(query)
    policy = evidence_policy_for(classification.category)

    assert classification.category is expected_category
    assert policy.category is classification.category


def test_evidence_policy_is_deeply_immutable():
    policy = evidence_policy_for(ResearchTaskCategory.FACTUAL_VERIFICATION)

    with pytest.raises(ValidationError):
        policy.authority_weight = 0.10
    with pytest.raises(TypeError):
        policy.preferred_source_types[0] = "web"


def test_evidence_policy_rejects_non_enum_category_resolution():
    with pytest.raises(TypeError):
        evidence_policy_for("factual_verification")


def test_evidence_policy_contract_rejects_weight_above_frozen_maximum():
    with pytest.raises(ValidationError):
        EvidencePolicy(
            policy_version=POLICY_VERSION,
            category=ResearchTaskCategory.FACTUAL_VERIFICATION,
            authority_weight=0.31,
            preferred_source_types=("official",),
            freshness_mode=FreshnessMode.CONTEXTUAL,
            max_age_days=365,
            corroboration_rule="primary_or_two_independent",
            primary_source_rule="required_or_two_independent",
            independent_source_rule="publisher_organization",
            reason_codes=("narrow_fact_direct_records",),
        )
