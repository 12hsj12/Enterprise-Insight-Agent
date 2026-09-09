"""Deterministic V2 research-task classification and evidence policies.

This module is intentionally independent of the retrieval and report-generation flows.
It defines the frozen V2 domain contracts without changing V1 runtime behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field


CLASSIFIER_VERSION: Final = "enterprise-insight-task-classifier/1.1.0"
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


# Clause features keep semantic ingredients separate.  In particular, source
# plurality does not imply a conflict and transition vocabulary does not imply a
# historical trend.  The structures are private because they are implementation
# details, not additions to the frozen public contract.
_SOURCE_MATERIAL = (
    r"(?:sources?|accounts?|claims?|disclosures?|records?|reports?|statements?|"
    r"evidence|documentation|reporting|data|descriptions?|licen[cs](?:e|ing)|"
    r"websites?|specifications?)"
)
_ZH_SOURCE_MATERIAL = r"(?:来源|说法|声明|披露|报告|记录|证据|数据|材料|描述|说明|文档|许可证(?:文本|信息)|发布页|官网)"
_SOURCE_ROLE = r"(?:official|vendor|marketing|regulator|operator|media|third[- ]party|independent)"
_ZH_SOURCE_ROLE = r"(?:官方|官网|厂商|营销|媒体|第三方|独立|监管|可复现)"

_SOURCE_PLURALITY = _compile(
    rf"\b(?:(?:the|a)\s+)?pair\s+of\s+{_SOURCE_MATERIAL}\b|"
    rf"\b(?:two|both|these\s+two|multiple|several|different)\s+"
    rf"(?:independent\s+)?{_SOURCE_MATERIAL}\b|"
    rf"\bwhich\s+source\b|\b(?:conflicting|contradictory|inconsistent)\s+{_SOURCE_MATERIAL}\b|"
    rf"\b(?:claims|disclosures|reports|records|accounts|sources|statements)\b|"
    rf"\b{_SOURCE_ROLE}\b.{{0,60}}\b(?:and|with|versus|vs\.?)\b.{{0,60}}\b{_SOURCE_ROLE}\b|"
    rf"\b{_SOURCE_ROLE}\b.{{0,60}}\b(?:and|with)\b.{{0,60}}\b{_SOURCE_MATERIAL}\b|"
    rf"\b{_SOURCE_MATERIAL}\b.{{0,60}}\b(?:and|with)\b.{{0,60}}\b{_SOURCE_ROLE}\b|"
    rf"\b{_SOURCE_MATERIAL}\b.{{0,90}}\b(?:and|with|versus|vs\.?)\b.{{0,90}}\b{_SOURCE_MATERIAL}\b|"
    rf"(?:两个|这两个|两份|这两份|两条|这两条|两方|双方|多个|多方|各方).{{0,12}}{_ZH_SOURCE_MATERIAL}|"
    rf"(?:哪个来源|相互冲突的证据)|{_ZH_SOURCE_ROLE}.{{0,50}}(?:与|和|及|、).{{0,50}}{_ZH_SOURCE_ROLE}|"
    rf"{_ZH_SOURCE_ROLE}.{{0,50}}(?:与|和|及|、).{{0,50}}{_ZH_SOURCE_MATERIAL}|"
    rf"{_ZH_SOURCE_MATERIAL}.{{0,50}}(?:与|和|及|、).{{0,50}}{_ZH_SOURCE_ROLE}|"
    rf"{_ZH_SOURCE_MATERIAL}.{{0,70}}(?:与|和|及|、).{{0,70}}{_ZH_SOURCE_MATERIAL}"
)
_RECONCILIATION_RELATION = _compile(
    r"\b(?:agree(?:ment)?|consistent|consistency|differ(?:ence|ences|ent)?|"
    r"disagree(?:ment)?|inconsisten(?:cy|t)|discrepanc(?:y|ies)|reconcil(?:e|es|ed|ing|iation)|"
    r"conflicting|conflict|contradict(?:ion|ory)?|credib(?:ility|le))\b|"
    r"一致|相符|吻合|差异|分歧|矛盾|冲突|不一致|可信"
)
_EXPLICIT_SHARED_ISSUE = _compile(
    r"\b(?:same|single)\s+(?:underlying\s+|material\s+)?"
    r"(?:issue|event|incident|outage|breach|transaction|merger|product|benchmark|"
    r"release|claim|fact|date|count|condition)\b|"
    r"同一|同次|同一次|对同一|关于同一|针对同一"
)
_SCOPED_SHARED_ISSUE = _compile(
    rf"\b{_SOURCE_MATERIAL}\b.{{0,40}}\b(?:of|on|about|regarding)\b\s+(?!different\b)|"
    r"\b(?:agree|consistent|differ|disagree|discrepancy)\b.{0,30}\b(?:on|about|regarding)\b|"
    r"\b(?:acquisition|merger|transaction|incident|outage|breach|release|launch)\b"
    r".{0,30}\b(?:date|count|condition|status)\b|"
    rf"{_ZH_SOURCE_MATERIAL}.{{0,30}}(?:对|关于|针对).{{1,50}}(?:是否一致|的差异|的分歧)|"
    r"(?:同一|同次|同一次).{0,40}(?:日期|数量|条件|状态|说法)"
)
_DIRECT_ACCOUNT_RELATION = _compile(
    rf"\b(?:conflicting|contradictory|inconsistent)\b.{{0,50}}\b{_SOURCE_MATERIAL}\b|"
    rf"\b(?:differences?|discrepanc(?:y|ies)|disagreement)\b.{{0,70}}\b{_SOURCE_MATERIAL}\b|"
    rf"\b{_SOURCE_MATERIAL}\b.{{0,90}}\b(?:agree|consistent|differ|disagree|"
    r"difference|differences|inconsistent|discrepancy|credible)\b|"
    r"\breconcil(?:e|es|ed|ing|iation)\b.{0,50}"
    r"\b(?:claims|disclosures|reports|accounts|statements)\b|"
    r"\bwhich\s+source\b.{0,30}\bcredible\b|"
    rf"{_ZH_SOURCE_MATERIAL}.{{0,70}}(?:是否)?(?:一致|相符|吻合|差异|分歧|矛盾|冲突|不一致|可信)"
)
_SOURCE_ROLE_PAIR = _compile(
    rf"\b{_SOURCE_ROLE}\b.{{0,60}}\b(?:and|with|versus|vs\.?)\b.{{0,60}}"
    rf"\b(?:{_SOURCE_ROLE}|reproduction)\b|"
    rf"{_ZH_SOURCE_ROLE}.{{0,50}}(?:与|和|及|、).{{0,50}}(?:{_ZH_SOURCE_ROLE}|复现)"
)

# Connector-symmetric cross-entity recognition blocks documents belonging to
# different comparison objects from being treated as accounts of one fact.
_CROSS_ENTITY = _compile(
    r"\b(?:two|both|different)\s+"
    r"(?:companies|products|vendors|datasets|platforms|services|systems|models)\b|"
    r"\btwo\s+vendors['’]?(?:s)?\b|\bseparate\s+products\b|"
    r"\b(company|product|vendor|dataset|platform|service|system|model)\s+[a-z0-9_-]+\b"
    r".{0,100}\b(?:and|with|versus|vs\.?)\b.{0,60}\b\1\s+[a-z0-9_-]+\b|"
    r"[甲乙丙丁].{0,2}(?:公司|产品|厂商|平台|数据集).{0,80}"
    r"[甲乙丙丁].{0,2}(?:公司|产品|厂商|平台|数据集)|"
    r"(?:公司|产品|厂商|平台|数据集)\s*[A-Za-z甲乙丙丁].{0,80}(?:与|和|及|对比|比较)"
    r".{0,50}(?:公司|产品|厂商|平台|数据集)\s*[A-Za-z甲乙丙丁]|"
    r"(?:两个|两家|不同)(?:产品|公司|厂商|平台|数据集)"
)

_TREND_WORD = _compile(r"\b(?:trends?|evolution|outlook)\b|趋势|演变|演进")
_EVOLUTION_RELATION = _compile(
    r"\b(?:evolution|evolv(?:e|es|ed|ing)|shift(?:s|ed|ing)?|transition(?:s|ed|ing)?|"
    r"develop(?:s|ed|ing)?|chang(?:e|es|ed|ing)|growth|adoption|trends?)\b|"
    r"\b(?:moving|evolving)\s+towards?\b|"
    r"(?:从|由).{1,100}(?:转向|走向|向|往).{1,100}|"
    r"(?:趋势|发展|演变|演进|转变|变化|增长|扩张|多样化|采用趋势|产品趋势)"
)
_STRONG_MACRO_SCOPE = _compile(
    r"\b(?:long[- ]term|historical|industry[- ]wide|sector[- ]wide|market[- ]wide|"
    r"market\s+adoption|ecosystem\s+evolution|sector\s+transition|across\s+generations|"
    r"over\s+(?:the\s+)?(?:last\s+|past\s+)?(?:several\s+|many\s+|\w+\s+)?years|"
    r"over\s+(?:the\s+)?last\s+decade|decades?)\b|"
    r"近年来|多年来|长期|历代|代际|行业演进|产业演进|市场采用(?:变化|趋势)|"
    r"生态演变|生态演进|行业变化|产业变化|行业证据|产业证据|"
    r"主要云厂商|数十年|几代|随时间"
)
_MACRO_DOMAIN_RELATION = _compile(
    r"\b(?:market|ecosystem|industry|sector|adoption)\b.{0,45}"
    r"\b(?:trends?|evolution|evolv(?:e|es|ed|ing)|moving|changes?|growth|"
    r"shift(?:s|ed|ing)?|transition|outlook|adoption)\b|"
    r"\b(?:trends?|evolution|evolv(?:e|es|ed|ing)|moving|changes?|growth|"
    r"shift(?:s|ed|ing)?|transition|outlook|adoption)\b.{0,45}"
    r"\b(?:market|ecosystem|industry|sector|adoption)\b|"
    r"(?:市场|生态|行业|产业|制造业|金融业|零售业|采用).{0,32}(?:趋势|演变|演进|变化|增长|扩张|转型|发展)|"
    r"(?:产品趋势|主要.{0,16}(?:厂商|供应商).{0,16}趋势|基础设施支出.{0,20}市场变化)"
)
_DISCIPLINE_EVOLUTION = _compile(
    r"\b(?:database|retrieval|communication|storage|software|ai|rag)\s+technolog(?:y|ies)\b"
    r".{0,100}\b(?:evolution|evolv(?:e|es|ed|ing)|develop(?:s|ed|ing)?)\b|"
    r"(?:数据库|检索|通信|存储|软件|人工智能|RAG)\s*技术.{0,100}(?:演进|发展)"
)
_DIRECTIONAL_EVOLUTION = _compile(
    r"\b(?:evolv(?:e|es|ed|ing)|shift(?:s|ed|ing)?|transition(?:s|ed|ing)?|"
    r"develop(?:s|ed|ing)?)\s+(?:of\b.{1,60})?from\b.{1,100}\b(?:to|towards?|into)\b|"
    r"\b(?:moving|evolving)\s+towards?\b|"
    r"(?:从|由).{1,100}(?:转向|走向|向|往).{1,100}(?:发展|演进|转变)?|"
    r"(?:正在|逐步|持续).{0,20}(?:向|往).{1,100}(?:发展|演进|转变)"
)
_RUNTIME_OPERATION = _compile(
    r"\b(?:runtime|during\s+execution|state\s+machine|service[- ]state|state\s+transition|"
    r"request\s+lifecycle|mode\s+switch|failover|queued\s+to\s+(?:active|running)|"
    r"leader\s+to\s+follower|idle\s+to\s+busy|training\s+to\s+(?:eval|evaluation)|"
    r"configuration\s+migration|single\s+deployment|schema\s+conversion|data\s+conversion|"
    r"protocol\s+transition|handshake\s+to\s+streaming)\b|"
    r"运行时|执行期间|状态机|状态转换|状态演变|故障转移|请求生命周期|模式切换|"
    r"排队.{0,8}(?:活动|运行)|主节点.{0,8}从节点|空闲.{0,8}忙碌|训练.{0,8}评估|"
    r"单次部署|单个配置.{0,12}迁移|模式转换|数据转换|协议转换"
)

_RECOMMENDATION_SIGNALS: Final = (
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
            r"(?:为|面向).{0,40}(?:选择|选用)|"
            r"(?:选择|选用).{0,30}(?:方案|平台|工具|组件)"
        ),
    ),
    ("explicit_roadmap", _compile(r"\broadmap\b|路线图|分阶段")),
)
_COMPARISON_SIGNAL = _compile(r"\bcompar(?:e|ing|ison)\b|\bversus\b|\bvs\.?\b|比较|对比")
_CROSS_ENTITY_COMPARISON_RELATION = _compile(
    r"\b(?:differences?|trade-?offs?|versus|vs\.?)\b|差异|取舍|权衡|对比|比较"
)
_TRADEOFF_SIGNAL = _compile(r"\btrade-?offs?\b|取舍|权衡")
_BETWEEN_ENTITY_TRADEOFF = _compile(r"\bbetween\b.{1,80}\band\b|多(?:产品|平台|方案)")
_VERIFICATION_SIGNAL = _compile(
    r"\b(?:verify|confirm|fact[- ]check|validate|check\s+whether)\b|"
    r"核实|核查|验证|事实核验"
)
_WHETHER_SIGNAL = _compile(r"\bwhether\b|\bis\s+it\b|是否|有没有|能否")
_NARROW_FACT_QUESTION = _compile(
    r"^\s*(?:is|are|does|do|did|has|have|can)\b.{0,120}"
    r"\b(?:available|accessible|published|released|allow|support|contain|include|licensed)\b"
)
_STATUS_CHECK_SIGNAL = _compile(
    r"\b(?:status|availability|release\s+date|launch\s+date)\b.{0,35}\b(?:verify|confirm|check)\b|"
    r"\b(?:verify|confirm|check)\b.{0,35}\b(?:status|availability|release\s+date|launch\s+date)\b|"
    r"(?:状态|可用性|可获得性|发布日期).{0,20}(?:核实|核查|确认)"
)
_TECHNICAL_ANALYSIS_SIGNAL = _compile(r"\b(?:technical|engineering)\s+analysis\b|技术分析|工程分析")
_CAPABILITY_SIGNAL = _compile(
    r"\b(?:capabilit(?:y|ies)|mechanism|architecture|internals?|algorithm|"
    r"handling|resolver|detection)\b|"
    r"能力|机制|架构|原理|算法|处理|检测"
)
_ANALYSIS_SIGNAL = _compile(
    r"\b(?:analy[sz]e|analysis|explain|describe|study|examine)\b|"
    r"分析|研究|解释|说明"
)
_LEXICAL_CONFLICT_SIGNAL = _compile(
    r"\b(?:conflict|contradict(?:ion|ory)?|reconcil(?:e|es|ed|ing|iation))\b|"
    r"冲突|矛盾|不一致"
)
_CREDIBILITY_SIGNAL = _compile(r"\bcredib(?:ility|le)\b|可信(?:度|性|判断)?|可信判断")
_CONFLICT_COREFERENCE = _compile(
    r"\b(?:they|their|both|these|those)\b|"
    r"^\s*(?:explain|determine|assess|resolve).{0,40}"
    r"(?:difference|discrepancy|agreement|consistency|conflict)|"
    r"二者|两者|这些|上述|其.{0,12}(?:说法|差异)|"
    r"^\s*(?:判断|解释|分析).{0,24}(?:差异|分歧|一致|冲突)"
)


@dataclass(frozen=True, slots=True)
class _ClauseFeatures:
    text: str
    source_plurality: bool
    reconciliation_relation: bool
    explicit_shared_issue: bool
    scoped_shared_issue: bool
    direct_account_relation: bool
    source_role_pair: bool
    cross_entity: bool
    evolution_relation: bool
    directional_evolution: bool
    strong_macro_scope: bool
    macro_domain_relation: bool
    discipline_evolution: bool
    runtime_operation: bool


@dataclass(frozen=True, slots=True)
class _TaskFeatures:
    normalized_query: str
    clauses: tuple[_ClauseFeatures, ...]
    conflict_clauses: tuple[_ClauseFeatures, ...]


def _clause_features(text: str) -> _ClauseFeatures:
    return _ClauseFeatures(
        text=text,
        source_plurality=bool(_SOURCE_PLURALITY.search(text)),
        reconciliation_relation=bool(_RECONCILIATION_RELATION.search(text)),
        explicit_shared_issue=bool(_EXPLICIT_SHARED_ISSUE.search(text)),
        scoped_shared_issue=bool(_SCOPED_SHARED_ISSUE.search(text)),
        direct_account_relation=bool(_DIRECT_ACCOUNT_RELATION.search(text)),
        source_role_pair=bool(_SOURCE_ROLE_PAIR.search(text)),
        cross_entity=bool(_CROSS_ENTITY.search(text)),
        evolution_relation=bool(_EVOLUTION_RELATION.search(text)),
        directional_evolution=bool(_DIRECTIONAL_EVOLUTION.search(text)),
        strong_macro_scope=bool(_STRONG_MACRO_SCOPE.search(text)),
        macro_domain_relation=bool(_MACRO_DOMAIN_RELATION.search(text)),
        discipline_evolution=bool(_DISCIPLINE_EVOLUTION.search(text)),
        runtime_operation=bool(_RUNTIME_OPERATION.search(text)),
    )


def _query_features(query: str) -> _TaskFeatures:
    normalized = " ".join(query.split())
    # Punctuation boundaries create local semantic clauses. Signals on opposite
    # sides cannot form a trend predicate. Conflict gets a narrow adjacent-clause
    # exception only when the second clause explicitly refers back to the first.
    hard_segments = tuple(
        segment.strip(" ,，:")
        for segment in re.split(r"[.!?。！？;；\r\n]+", normalized)
        if segment.strip(" ,，:")
    )
    clause_groups = tuple(
        tuple(
            clause.strip(" ,，:")
            for clause in re.split(r"[,，]+", segment)
            if clause.strip(" ,，:")
        )
        for segment in hard_segments
    )
    clause_texts = tuple(clause for group in clause_groups for clause in group)
    conflict_texts = list(clause_texts)
    for group in clause_groups:
        for left, right in zip(group, group[1:]):
            if _CONFLICT_COREFERENCE.search(right):
                conflict_texts.append(f"{left}, {right}")
    return _TaskFeatures(
        normalized_query=normalized,
        clauses=tuple(_clause_features(clause) for clause in clause_texts),
        conflict_clauses=tuple(
            _clause_features(clause) for clause in conflict_texts
        ),
    )


def _matching_codes(text: str, signals: tuple[tuple[str, re.Pattern[str]], ...]) -> tuple[str, ...]:
    return tuple(code for code, pattern in signals if pattern.search(text))


def _is_conflict_clause(clause: _ClauseFeatures) -> bool:
    if not clause.source_plurality or not clause.reconciliation_relation:
        return False
    same_issue = (
        clause.explicit_shared_issue
        or clause.scoped_shared_issue
        or clause.direct_account_relation
    )
    if not same_issue:
        return False
    return not clause.cross_entity or clause.explicit_shared_issue


def _is_conflict_intent(features: _TaskFeatures) -> tuple[str, ...]:
    matching = tuple(
        clause for clause in features.conflict_clauses if _is_conflict_clause(clause)
    )
    if not matching:
        return ()
    codes: list[str] = []
    text = features.normalized_query
    if _LEXICAL_CONFLICT_SIGNAL.search(text):
        codes.append("explicit_conflict")
    if _CREDIBILITY_SIGNAL.search(text):
        codes.append("explicit_credibility")
    if any(clause.source_role_pair for clause in matching):
        codes.append("claim_replication_difference")
    if re.search(r"各方.{0,20}(?:说法|证据)|双方.{0,20}(?:说法|证据)|material\s+sides", text, re.I):
        codes.append("material_sides_resolution")
    codes.append("source_account_consistency")
    return tuple(codes)


def _is_trend_clause(clause: _ClauseFeatures) -> bool:
    if not clause.evolution_relation:
        return False
    macro_scope = (
        clause.strong_macro_scope
        or clause.macro_domain_relation
        or clause.discipline_evolution
    )
    if not macro_scope:
        return False
    # Runtime/state operations are technical unless the same clause independently
    # establishes an explicit historical, adoption, ecosystem, or market scope.
    if clause.runtime_operation and not (
        clause.strong_macro_scope or clause.macro_domain_relation
    ):
        return False
    return True


def _is_trend_intent(features: _TaskFeatures) -> tuple[str, ...]:
    matching = tuple(clause for clause in features.clauses if _is_trend_clause(clause))
    if not matching:
        return ()
    codes: list[str] = []
    if any(_TREND_WORD.search(clause.text) for clause in matching):
        codes.append("explicit_trend")
    if any(clause.strong_macro_scope or clause.macro_domain_relation for clause in matching):
        codes.append("market_change_over_time")
    if any(clause.directional_evolution for clause in matching):
        codes.append("temporal_process_evolution")
    return tuple(codes or ["temporal_process_evolution"])


def _is_comparison_intent(features: _TaskFeatures) -> tuple[str, ...]:
    text = features.normalized_query
    codes: list[str] = []
    if _COMPARISON_SIGNAL.search(text) or (
        any(clause.cross_entity for clause in features.clauses)
        and _CROSS_ENTITY_COMPARISON_RELATION.search(text)
    ):
        codes.append("explicit_comparison")
    if _TRADEOFF_SIGNAL.search(text) and (
        _BETWEEN_ENTITY_TRADEOFF.search(text)
        or any(clause.cross_entity for clause in features.clauses)
    ):
        codes.append("multi_entity_tradeoff")
    return tuple(codes)


def _is_factual_intent(features: _TaskFeatures) -> tuple[str, ...]:
    text = features.normalized_query
    codes: list[str] = []
    if _VERIFICATION_SIGNAL.search(text):
        codes.append("explicit_verification")
    if _WHETHER_SIGNAL.search(text) or _NARROW_FACT_QUESTION.search(text):
        codes.append("narrow_whether_question")
    if _STATUS_CHECK_SIGNAL.search(text):
        codes.append("status_availability_check")
    return tuple(codes)


def _is_technical_intent(features: _TaskFeatures) -> tuple[str, ...]:
    text = features.normalized_query
    codes: list[str] = []
    if _TECHNICAL_ANALYSIS_SIGNAL.search(text):
        codes.append("technical_analysis")
    if _CAPABILITY_SIGNAL.search(text):
        codes.append("capability_mechanism")
    if _ANALYSIS_SIGNAL.search(text):
        codes.append("explicit_analysis")
    return tuple(codes)


def _is_recommendation_intent(features: _TaskFeatures) -> tuple[str, ...]:
    return _matching_codes(features.normalized_query, _RECOMMENDATION_SIGNALS)


def _category_signal_codes(
    category: ResearchTaskCategory,
    features: _TaskFeatures,
) -> tuple[str, ...]:
    predicates = {
        ResearchTaskCategory.ENTERPRISE_DECISION_RECOMMENDATION: _is_recommendation_intent,
        ResearchTaskCategory.CONFLICT_CREDIBILITY_RESOLUTION: _is_conflict_intent,
        ResearchTaskCategory.COMPETITIVE_COMPARISON: _is_comparison_intent,
        ResearchTaskCategory.TREND_MARKET_INTELLIGENCE: _is_trend_intent,
        ResearchTaskCategory.FACTUAL_VERIFICATION: _is_factual_intent,
        ResearchTaskCategory.TECHNICAL_CAPABILITY_ANALYSIS: _is_technical_intent,
    }
    return predicates[category](features)

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

        features = _query_features(query)
        matched_by_category: dict[ResearchTaskCategory, list[str]] = {}

        for category in _PRECEDENCE:
            category_codes = list(_category_signal_codes(category, features))
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
