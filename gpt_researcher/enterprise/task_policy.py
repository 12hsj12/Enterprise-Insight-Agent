"""Deterministic V2 research-task classification and evidence policies.

This module is intentionally independent of the retrieval and report-generation flows.
It defines the frozen V2 domain contracts without changing V1 runtime behavior.
"""

from __future__ import annotations

import re
from enum import Enum
from types import MappingProxyType
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field


CLASSIFIER_VERSION: Final = "enterprise-insight-task-classifier/1.0.2"
POLICY_VERSION: Final = "enterprise-insight-v2-architecture/2.0.0"

# The current web evidence model has URL provenance, but not publication timestamps,
# publisher ownership, or the richer source-role vocabulary required to enforce these
# policy fields honestly.  Keep the requirements typed and make the boundary auditable
# until claim grounding owns the corresponding checks.
EVIDENCE_SELECTION_LIMITATION_CODES: Final = (
    "preferred_source_types_not_enforced_missing_structured_provenance",
    "freshness_not_enforced_missing_publication_time",
    "corroboration_deferred_to_claim_grounding",
    "primary_source_rule_deferred_to_claim_grounding",
    "independence_rule_deferred_to_claim_grounding",
)

PublicCode = Annotated[
    str,
    Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$"),
]


class ResearchTaskCategory(str, Enum):
    """Closed V2 enterprise-intelligence task taxonomy."""

    FACTUAL_VERIFICATION = "factual_verification"
    TECHNICAL_CAPABILITY_ANALYSIS = "technical_capability_analysis"
    COMPETITIVE_COMPARISON = "competitive_comparison"
    TREND_MARKET_INTELLIGENCE = "trend_market_intelligence"
    CONFLICT_CREDIBILITY_RESOLUTION = "conflict_credibility_resolution"
    ENTERPRISE_DECISION_RECOMMENDATION = "enterprise_decision_recommendation"


class FreshnessMode(str, Enum):
    """How evidence age should be interpreted by later V2 retrieval work."""

    NOT_REQUIRED = "not_required"
    CONTEXTUAL = "contextual"
    STRICT = "strict"


class TaskClassification(BaseModel):
    """Public, auditable output from the deterministic task classifier.

    ``confidence`` describes only confidence in the task category. It is not a
    source-reliability score, factual confidence, or claim truth probability.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: ResearchTaskCategory
    confidence: float = Field(ge=0.0, le=1.0)
    classifier_version: str = Field(min_length=1)
    matched_signal_codes: list[PublicCode]
    runner_up_categories: list[ResearchTaskCategory]
    rationale_codes: list[PublicCode]
    fallback_used: bool


class EvidencePolicy(BaseModel):
    """Immutable task-aware source-selection policy for later V2 integration.

    ``authority_weight`` remains a source-level reliability prior. The frozen
    maximum of 0.30 preserves semantic relevance as the dominant ranking signal.
    Tuples make collection fields immutable as well as the model itself.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    policy_version: str = Field(min_length=1)
    category: ResearchTaskCategory
    authority_weight: float = Field(ge=0.0, le=0.30)
    preferred_source_types: tuple[PublicCode, ...] = Field(min_length=1)
    freshness_mode: FreshnessMode
    max_age_days: int | None = Field(default=None, ge=1)
    corroboration_rule: PublicCode
    primary_source_rule: PublicCode
    independent_source_rule: PublicCode
    reason_codes: tuple[PublicCode, ...] = Field(min_length=1)


_PRECEDENCE: Final = (
    ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION,
    ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION,
    ResearchTaskCategory.COMPETITIVE_COMPARISON,
    ResearchTaskCategory.TREND_MARKET_INTELLIGENCE,
    ResearchTaskCategory.FACTUAL_VERIFICATION,
    ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS,
)


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# These features are deliberately separate: materials are not necessarily accounts
# of one fact, and a directional operation is not necessarily historical evolution.
_SOURCE_MATERIAL = (
    r"\b(?:sources?|accounts?|claims?|disclosures?|records?|reports?|statements?|"
    r"documentation|reporting|data|descriptions?|licen[cs](?:e|ing)|websites?)\b|"
    r"来源|说法|声明|披露|报告|记录|数据|材料|描述|说明|文档|许可证(?:文本|信息)|发布页|官网"
)
_SOURCE_PLURALITY = _compile(
    r"\b(?:two|both|these|multiple|different)\s+(?:authoritative\s+)?"
    r"(?:sources|accounts|claims|disclosures|records|reports)\b|"
    r"(?:不同|多个|多方|各方|双方|两方|两[个份条]).{0,12}"
    r"(?:来源|说法|声明|披露|报告|记录|材料)|"
    rf"(?:{_SOURCE_MATERIAL}).{{0,80}}(?:\band\b|\bwith\b|\bversus\b|与|和|及|、)"
    rf".{{0,80}}(?:{_SOURCE_MATERIAL})"
)
_SOURCE_ROLES = _compile(
    r"\b(?:official|vendor|marketing|regulator|operator|media|third[- ]party|independent|replication)\b"
    r".{0,80}\b(?:and|versus|with)\b.{0,80}"
    r"\b(?:official|vendor|marketing|regulator|operator|media|third[- ]party|independent|replication)\b|"
    r"(?:官方|官网|厂商|营销|媒体|第三方|独立|监管|(?:可)?复现).{0,50}(?:与|和|及|、).{0,50}"
    r"(?:官方|官网|厂商|营销|媒体|第三方|独立|监管|(?:可)?复现)"
)
_ACCOUNT_RELATION = _compile(
    r"\b(?:agree(?:ment)?|consistent|consistency|differ(?:ence|ences|ent)?|"
    r"disagree(?:ment)?|inconsisten(?:cy|t)|discrepanc(?:y|ies)|reconcile|"
    r"contradict(?:ion|ory)?|credibility)\b|一致|相符|吻合|差异|分歧|矛盾|冲突|可信"
)
_EXPLICIT_SHARED_ISSUE = _compile(
    r"\b(?:same|single)\s+(?:underlying\s+|material\s+)?"
    r"(?:issue|event|incident|outage|breach|entity|product|claim|fact|release|merger|transaction)\b|"
    r"同一|同次|同一次"
)
_SCOPED_ACCOUNT_TOPIC = _compile(
    r"\b(?:on|about|regarding)\s+(?:the|a|one)\s+|关于|针对|"
    r"核查.{1,60}的.{1,60}(?:声明|许可证|报告|说法)"
)
# Repeated entity heads or explicit collective products defeat implicit coreference.
# An explicit shared issue can still establish reconciliation across their accounts.
_CROSS_ENTITY = _compile(
    r"\b(?:two|both|different)\s+(?:companies|products|vendors|datasets|platforms)\b|"
    r"\b(company|product|vendor|dataset|platform)\s+\w+.{0,80}"
    r"\b(?:and|versus|vs)\b.{0,40}\b\1\s+\w+|"
    r"[甲乙丙丁].{0,2}(?:公司|产品|厂商).{0,60}[甲乙丙丁].{0,2}(?:公司|产品|厂商)|"
    r"(?:两个|两家|双方|不同)(?:产品|公司|厂商|平台)"
)
_ACCOUNT_ASSERTION = _compile(
    r"\b(?:sources|accounts|claims|disclosures|statements|reports)\b|"
    r"来源|说法|声明|披露|许可证|描述"
)


def _source_account_consistency(query: str) -> bool:
    """Require plurality, a relation, and shared-fact or account-reconciliation intent.

    Role-paired accounts and consistency of assertions can imply a shared issue
    when no distinct entity context intervenes. Bare material differences cannot.
    This is conservative query syntax, not general-purpose coreference resolution.
    """
    roles = bool(_SOURCE_ROLES.search(query))
    plural = roles or bool(_SOURCE_PLURALITY.search(query))
    if not plural or not _ACCOUNT_RELATION.search(query):
        return False
    if _EXPLICIT_SHARED_ISSUE.search(query):
        return True
    if _CROSS_ENTITY.search(query):
        return False
    assertion_consistency = bool(_ACCOUNT_ASSERTION.search(query)) and bool(
        re.search(r"\bagree\b|\bconsisten(?:t|cy)\b|一致|相符|吻合|可信", query, re.I)
    )
    return bool(_SCOPED_ACCOUNT_TOPIC.search(query)) or roles or assertion_consistency


_MACRO_TEMPORAL_SCOPE = _compile(
    r"\b(?:markets?|ecosystems?|industr(?:y|ies)|sectors?|adoption|historical|"
    r"long[- ]term|decades?|generations?)\b|\bover (?:the )?(?:last |past )?(?:\w+ )?years\b|"
    r"市场|生态|行业|产业|采用|长期|历年|近年来|多年来|数十年|几代|代际"
)
_EVOLUTION_PROCESS = _compile(
    r"\b(?:evolv(?:e|es|ed|ing)|shift(?:s|ed|ing)?|transition(?:s|ed|ing)?|"
    r"develop(?:s|ed|ing)?)\s+(?:of\b.{1,60})?from\b.{1,100}\b(?:to|towards?|into)\b|"
    r"\b(?:moving|evolving)\s+towards?\b|"
    r"(?:从|由).{1,100}(?:(?:向|往).{1,100}(?:发展|演进|转变)|(?:转向|走向).{1,100})|"
    r"(?:正在|逐步|持续).{0,16}(?:向|往).{1,100}(?:发展|演进|转变)|"
    r"\bevolution\b|演进"
)
# Evolution of a technical discipline is a scope in its own right; a technology
# noun next to a runtime shift is not. Require development/evolution language.
_DISCIPLINE_EVOLUTION = _compile(
    r"\btechnolog(?:y|ies)\b.{0,100}\b(?:evolution|evolv(?:e|es|ed|ing))\b|"
    r"技术.{0,100}(?:演进|发展)"
)


def _temporal_process_evolution(query: str) -> bool:
    return bool(_EVOLUTION_PROCESS.search(query)) and bool(
        _MACRO_TEMPORAL_SCOPE.search(query) or _DISCIPLINE_EVOLUTION.search(query)
    )


_SIGNALS: Final = MappingProxyType(
    {
        ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION: (
            (
                "explicit_recommendation",
                _compile(r"\b(?:recommend|recommendation|advise|advice)\b|推荐|建议"),
            ),
            (
                "explicit_decision",
                _compile(
                    r"\bdecision\s+(?:framework|criteria)\b|决策框架|"
                    r"应(?:当|该)?优先|判断应(?:当|该)?|给出.{0,24}(?:建议|路线图)"
                ),
            ),
            (
                "explicit_option_selection",
                _compile(
                    r"\bshould\b.{0,40}\b(?:choose|select|adopt|prioriti[sz]e)\b|"
                    r"(?:为|面向).{0,40}(?:选择|选用)|(?:选择|选用).{0,30}(?:方案|平台|工具|组件)"
                ),
            ),
            ("explicit_roadmap", _compile(r"\broadmap\b|路线图|分阶段")),
        ),
        ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION: (
            (
                "explicit_conflict",
                _compile(
                    r"\b(?:conflict|contradict(?:ion|ory)?|reconcile)\b|冲突|矛盾|不一致"
                ),
            ),
            (
                "explicit_credibility",
                _compile(r"\bcredib(?:ility|le)\b|可信(?:度|性|判断)?|可信判断"),
            ),
            (
                "claim_replication_difference",
                _compile(
                    r"(?:官方|厂商|营销).{0,40}(?:独立|第三方|复现).{0,40}(?:差异|一致)|"
                    r"(?:独立|第三方|复现).{0,40}(?:官方|厂商|营销).{0,40}(?:差异|一致)|"
                    r"\b(?:official|vendor|marketing).{0,50}(?:independent|third[- ]party|replicat).{0,50}"
                    r"(?:differ|discrep|consistent)"
                ),
            ),
            (
                "material_sides_resolution",
                _compile(r"各方.{0,20}(?:说法|证据)|双方.{0,20}(?:说法|证据)|material\s+sides"),
            ),
        ),
        ResearchTaskCategory.COMPETITIVE_COMPARISON: (
            (
                "explicit_comparison",
                _compile(r"\bcompar(?:e|ing|ison)\b|\bversus\b|\bvs\.?\b|比较|对比"),
            ),
            (
                "multi_entity_tradeoff",
                _compile(r"\bbetween\b.{1,80}\band\b.{1,40}\btrade-?offs?\b|多(?:产品|平台|方案).{0,20}取舍"),
            ),
        ),
        ResearchTaskCategory.TREND_MARKET_INTELLIGENCE: (
            (
                "explicit_trend",
                _compile(r"\btrends?\b|趋势|演变"),
            ),
            (
                "market_change_over_time",
                _compile(
                    r"\bmarket\b.{0,40}\b(?:growth|change|evolution|adoption|outlook)\b|"
                    r"\b(?:growth|change|evolution|adoption)\b.{0,40}\bmarket\b|"
                    r"市场.{0,20}(?:变化|增长|演进|采用|前景)|(?:历年|近年来|随时间)"
                ),
            ),
        ),
        ResearchTaskCategory.FACTUAL_VERIFICATION: (
            (
                "explicit_verification",
                _compile(r"\b(?:verify|confirm|fact[- ]check|validate)\b|核实|核查|验证|事实核验"),
            ),
            (
                "narrow_whether_question",
                _compile(r"\bwhether\b|\bis\s+it\b|是否|有没有|能否"),
            ),
            (
                "status_availability_check",
                _compile(
                    r"\b(?:status|availability)\b.{0,30}\b(?:verify|confirm|check)\b|"
                    r"\b(?:verify|confirm|check)\b.{0,30}\b(?:status|availability)\b|"
                    r"(?:状态|可用性|可获得性).{0,20}(?:核实|核查|确认)"
                ),
            ),
        ),
        ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS: (
            (
                "technical_analysis",
                _compile(r"\b(?:technical|engineering)\s+analysis\b|技术分析|工程分析"),
            ),
            (
                "capability_mechanism",
                _compile(r"\b(?:capabilit(?:y|ies)|mechanism|architecture|internals?)\b|能力|机制|架构|原理"),
            ),
            (
                "explicit_analysis",
                _compile(r"\b(?:analy[sz]e|analysis)\b|分析"),
            ),
        ),
    }
)

# These versioned heuristic scores describe rule clarity, not calibrated probability.
# More matching signals increase clarity; overlapping intents reduce it.
_FALLBACK_CONFIDENCE: Final = 0.35
_BASE_MATCH_CONFIDENCE: Final = 0.80
_PER_WINNING_SIGNAL_BONUS: Final = 0.05
_OVERLAP_PENALTY: Final = 0.10
_MAX_RULE_CONFIDENCE: Final = 0.95

_CATEGORY_REASON: Final = MappingProxyType(
    {
        ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION: "selected_explicit_decision",
        ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION: "selected_conflict_resolution",
        ResearchTaskCategory.COMPETITIVE_COMPARISON: "selected_multi_entity_comparison",
        ResearchTaskCategory.TREND_MARKET_INTELLIGENCE: "selected_time_market_trend",
        ResearchTaskCategory.FACTUAL_VERIFICATION: "selected_narrow_fact_verification",
        ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS: "selected_technical_analysis",
    }
)


class ResearchTaskClassifier:
    """Classify only the query text using stable, deterministic public signals."""

    version = CLASSIFIER_VERSION

    def classify(self, query: str) -> TaskClassification:
        if not isinstance(query, str):
            raise TypeError("query must be a string")

        normalized_query = " ".join(query.split())
        matched_by_category: dict[ResearchTaskCategory, list[str]] = {}

        for category in _PRECEDENCE:
            category_codes = [
                code
                for code, pattern in _SIGNALS[category]
                if pattern.search(normalized_query)
            ]
            # Legacy source-role signals must obey the same boundary as the new
            # collective-source signal, rather than bypassing its entity check.
            if category is ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION:
                if _source_account_consistency(normalized_query):
                    category_codes.append("source_account_consistency")
                else:
                    category_codes = [
                        code for code in category_codes
                        if code not in {
                            "claim_replication_difference", "material_sides_resolution"
                        }
                    ]
            if (
                category is ResearchTaskCategory.TREND_MARKET_INTELLIGENCE
                and _temporal_process_evolution(normalized_query)
            ):
                category_codes.append("temporal_process_evolution")
            if category_codes:
                matched_by_category[category] = category_codes

        matched_categories = [
            category for category in _PRECEDENCE if category in matched_by_category
        ]
        if not matched_categories:
            return TaskClassification(
                category=ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS,
                confidence=_FALLBACK_CONFIDENCE,
                classifier_version=self.version,
                matched_signal_codes=[],
                runner_up_categories=[],
                rationale_codes=[
                    "no_explicit_task_signal",
                    "fallback_unresolved_signal_tie",
                ],
                fallback_used=True,
            )

        category = matched_categories[0]
        runner_ups = matched_categories[1:]
        winning_signal_count = len(matched_by_category[category])
        confidence = _BASE_MATCH_CONFIDENCE
        confidence += _PER_WINNING_SIGNAL_BONUS * winning_signal_count
        if runner_ups:
            confidence -= _OVERLAP_PENALTY
        confidence = round(min(confidence, _MAX_RULE_CONFIDENCE), 2)

        rationale_codes = [_CATEGORY_REASON[category]]
        if runner_ups:
            rationale_codes.append("frozen_precedence_applied")

        return TaskClassification(
            category=category,
            confidence=confidence,
            classifier_version=self.version,
            matched_signal_codes=[
                code
                for matched_category in matched_categories
                for code in matched_by_category[matched_category]
            ],
            runner_up_categories=runner_ups,
            rationale_codes=rationale_codes,
            fallback_used=False,
        )


_EVIDENCE_POLICIES: Final = MappingProxyType(
    {
        ResearchTaskCategory.FACTUAL_VERIFICATION: EvidencePolicy(
            policy_version=POLICY_VERSION,
            category=ResearchTaskCategory.FACTUAL_VERIFICATION,
            authority_weight=0.30,
            preferred_source_types=(
                "official",
                "regulator_standard",
                "official_documentation",
                "authoritative_media",
            ),
            freshness_mode=FreshnessMode.CONTEXTUAL,
            max_age_days=365,
            corroboration_rule="primary_or_two_independent",
            primary_source_rule="required_or_two_independent",
            independent_source_rule="publisher_organization",
            reason_codes=("narrow_fact_direct_records",),
        ),
        ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS: EvidencePolicy(
            policy_version=POLICY_VERSION,
            category=ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS,
            authority_weight=0.22,
            preferred_source_types=(
                "official_documentation",
                "peer_reviewed_research",
                "regulator_standard",
                "independent_technical",
            ),
            freshness_mode=FreshnessMode.CONTEXTUAL,
            max_age_days=730,
            corroboration_rule="primary_plus_independent",
            primary_source_rule="preferred",
            independent_source_rule="publisher_organization",
            reason_codes=("technical_specificity_primary",),
        ),
        ResearchTaskCategory.COMPETITIVE_COMPARISON: EvidencePolicy(
            policy_version=POLICY_VERSION,
            category=ResearchTaskCategory.COMPETITIVE_COMPARISON,
            authority_weight=0.10,
            preferred_source_types=(
                "official_documentation",
                "independent_technical",
                "authoritative_media",
                "peer_reviewed_research",
            ),
            freshness_mode=FreshnessMode.STRICT,
            max_age_days=365,
            corroboration_rule="primary_plus_independent",
            primary_source_rule="one_per_compared_entity",
            independent_source_rule="publisher_organization",
            reason_codes=("symmetric_entity_evidence",),
        ),
        ResearchTaskCategory.TREND_MARKET_INTELLIGENCE: EvidencePolicy(
            policy_version=POLICY_VERSION,
            category=ResearchTaskCategory.TREND_MARKET_INTELLIGENCE,
            authority_weight=0.12,
            preferred_source_types=(
                "regulator_standard",
                "authoritative_media",
                "industry_analysis",
                "official",
            ),
            freshness_mode=FreshnessMode.STRICT,
            max_age_days=180,
            corroboration_rule="two_independent",
            primary_source_rule="preferred_for_measured_inputs",
            independent_source_rule="publisher_organization",
            reason_codes=("trend_recency_source_diversity",),
        ),
        ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION: EvidencePolicy(
            policy_version=POLICY_VERSION,
            category=ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION,
            authority_weight=0.18,
            preferred_source_types=(
                "regulator_standard",
                "official_documentation",
                "peer_reviewed_research",
                "authoritative_media",
            ),
            freshness_mode=FreshnessMode.CONTEXTUAL,
            max_age_days=365,
            corroboration_rule="conflict_sides_plus_adjudicator",
            primary_source_rule="source_for_each_material_side",
            independent_source_rule="publisher_organization",
            reason_codes=("preserve_material_disagreement",),
        ),
        ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION: EvidencePolicy(
            policy_version=POLICY_VERSION,
            category=ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION,
            authority_weight=0.08,
            preferred_source_types=(
                "official_documentation",
                "independent_technical",
                "industry_analysis",
                "peer_reviewed_research",
            ),
            freshness_mode=FreshnessMode.CONTEXTUAL,
            max_age_days=730,
            corroboration_rule="two_independent",
            primary_source_rule="preferred",
            independent_source_rule="publisher_organization",
            reason_codes=("premise_uncertainty_multi_family",),
        ),
    }
)


def evidence_policy_for(category: ResearchTaskCategory) -> EvidencePolicy:
    """Return the immutable frozen policy for a classified task category."""

    if not isinstance(category, ResearchTaskCategory):
        raise TypeError("category must be a ResearchTaskCategory")
    return _EVIDENCE_POLICIES[category]


__all__ = [
    "CLASSIFIER_VERSION",
    "EVIDENCE_SELECTION_LIMITATION_CODES",
    "POLICY_VERSION",
    "EvidencePolicy",
    "FreshnessMode",
    "ResearchTaskCategory",
    "ResearchTaskClassifier",
    "TaskClassification",
    "evidence_policy_for",
]
