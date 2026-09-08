import inspect

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
