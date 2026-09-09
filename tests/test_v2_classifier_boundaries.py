"""Query-only semantic boundaries; every expectation has a taxonomy justification.

This worker-authored adversarial matrix is not an independent reviewer approval.
The production classifier neither imports these examples nor reads the dataset.
"""

import pytest

from gpt_researcher.enterprise.task_policy import ResearchTaskCategory as Category
from gpt_researcher.enterprise.task_policy import ResearchTaskClassifier


TECHNICAL = Category.TECHNICAL_CAPABILITY_ANALYSIS
TREND = Category.TREND_MARKET_INTELLIGENCE
COMPARISON = Category.COMPETITIVE_COMPARISON
CONFLICT = Category.CONFLICT_CREDIBILITY_RESOLUTION
FACTUAL = Category.FACTUAL_VERIFICATION
DECISION = Category.ENTERPRISE_DECISION_RECOMMENDATION

# Tuples contain query, expected category, and the public semantic justification.
TREND_TECHNICAL = [
    ("Explain how a storage service transitions from leader to follower during runtime.", TECHNICAL, "Runtime role change"),
    ("Describe why a model shifts from training to evaluation mode after eval().", TECHNICAL, "Runtime mode switch"),
    ("分析连接池由空闲转向忙碌状态的锁机制。", TECHNICAL, "Runtime pool state"),
    ("Explain how a platform request transitions from queued to running in its state machine.", TECHNICAL, "Request lifecycle"),
    ("Analyze how one service platform configuration moves from cluster X to cluster Y.", TECHNICAL, "Single configuration operation"),
    ("Describe a schema conversion and package upgrade for the model service architecture.", TECHNICAL, "Deployment operations"),
    ("Explain the long-term shift of the retail ecosystem from stores toward digital marketplaces.", TREND, "Long-term ecosystem development"),
    ("分析制造业采用自动化技术从局部试点向规模部署发展的过程。", TREND, "Industry adoption development"),
    ("Study how the hosting market shifted from owned servers to rented capacity over twenty years.", TREND, "Multi-period market change"),
    ("研究通信技术跨越几代系统从模拟向数字演进的过程。", TREND, "Generational technology development"),
    ("分析数据基础设施从集中部署转向分布式平台的演进过程。", TECHNICAL, "No historical or discipline scope established"),
    ("Study the technology transition from on-premise platforms to managed services.", TECHNICAL, "Technology noun alone supplies no macro scope"),
    ("Analyze why retrieval technology is shifting from dense-only search toward hybrid search.", TECHNICAL, "Shift alone is ambiguous without adoption scope"),
    ("Examine how enterprise AI platforms are moving toward governed agent workflows.", TECHNICAL, "Platforms alone do not establish macro scope"),
]

CONFLICT_COMPARISON = [
    ("比较甲公司官网与乙公司官网的字体和无障碍设计差异。", COMPARISON, "Different company sites are comparison objects"),
    ("Compare Product Cedar documentation and Product Birch documentation for navigation differences.", COMPARISON, "Different product documents"),
    ("Compare Company Cedar revenue data and Company Birch revenue data in magnitude.", COMPARISON, "Different entity revenues"),
    ("Compare two vendors' published specifications for memory capacity.", COMPARISON, "Different vendor specifications"),
    ("Compare Dataset Cedar versus Dataset Birch for missing values.", COMPARISON, "Different datasets"),
    ("Are two products' specifications consistent?", TECHNICAL, "Compatibility ambiguity is not source reconciliation"),
    ("Compare official and independent accounts of the same security incident and explain discrepancies.", CONFLICT, "Accounts of one incident"),
    ("比较官网与监管记录对同一产品发布日期的说法是否一致。", CONFLICT, "Shared release fact wins over comparison"),
    ("Compare two reports about different companies and explain layout differences.", COMPARISON, "Plural reports alone do not imply shared issue"),
    ("Compare independent Product Cedar documentation and official Product Birch documentation for differences.", COMPARISON, "Source roles do not override distinct products"),
    ("Compare official Product Cedar documentation and independent Product Birch documentation for differences.", COMPARISON, "Reversed roles still concern different products"),
    ("Compare Company Cedar data and Company Birch data on the revenue differences.", COMPARISON, "A topic preposition does not establish the same fact"),
]

CONFLICT_FACTUAL = [
    ("Assess whether two sources agree on the acquisition completion date.", CONFLICT, "Agreement on one transaction date"),
    ("Check whether both reports agree on the customer count for the same network outage.", CONFLICT, "Agreement on one outage count"),
    ("核查两份报告对同一次并购的完成日期是否一致。", CONFLICT, "Dual-source same-event verification"),
    ("Verify whether the product release date has been announced.", FACTUAL, "Single status fact"),
    ("核查产品是否已经向公众开放。", FACTUAL, "Single availability fact"),
    ("Check whether two records contain a publication date.", FACTUAL, "Plurality without reconciliation"),
    ("核查某数据库关于事务吞吐的营销声明与可复现实验的差异。", CONFLICT, "A replication tests the same advertised claim"),
]

MIXED_PRECEDENCE = [
    ("Recommend a response after comparing two sources that disagree on the same incident date.", DECISION, "Recommendation precedes reconciliation and comparison"),
    ("核查并比较两个来源对同一交易金额的说法是否一致。", CONFLICT, "Reconciliation precedes comparison and factual check"),
    ("Compare two platforms and verify their market adoption trends.", COMPARISON, "Comparison precedes trend and verification"),
    ("核查市场从本地部署向托管服务长期演进的证据。", TREND, "Temporal scope precedes verification"),
]


@pytest.mark.parametrize("query,expected,reason", TREND_TECHNICAL)
def test_trend_technical_boundary(query, expected, reason):
    result = ResearchTaskClassifier().classify(query)
    assert result.category is expected, reason
    if expected is TECHNICAL:
        assert "temporal_process_evolution" not in result.matched_signal_codes


@pytest.mark.parametrize("query,expected,reason", CONFLICT_COMPARISON)
def test_conflict_comparison_boundary(query, expected, reason):
    result = ResearchTaskClassifier().classify(query)
    assert result.category is expected, reason
    if expected is not CONFLICT:
        assert "source_account_consistency" not in result.matched_signal_codes


@pytest.mark.parametrize("query,expected,reason", CONFLICT_FACTUAL)
def test_conflict_factual_boundary(query, expected, reason):
    assert ResearchTaskClassifier().classify(query).category is expected, reason


@pytest.mark.parametrize("query,expected,reason", MIXED_PRECEDENCE)
def test_mixed_precedence_boundary(query, expected, reason):
    result = ResearchTaskClassifier().classify(query)
    assert result.category is expected, reason
    assert "frozen_precedence_applied" in result.rationale_codes


@pytest.mark.parametrize("sources", [
    "two sources", "both sources", "two reports", "both reports", "two records",
    "both records", "the two accounts", "these sources", "multiple accounts",
    "independent and official sources", "the website and regulator record",
])
def test_english_collective_accounts_need_a_relation(sources):
    classifier = ResearchTaskClassifier()
    result = classifier.classify(f"Assess whether {sources} agree on the same event date.")
    assert result.category is CONFLICT
    assert "source_account_consistency" in result.matched_signal_codes
    assert classifier.classify(f"Check whether {sources} are available.").category is FACTUAL


@pytest.mark.parametrize("sources", [
    "两个来源", "两份报告", "两条记录", "双方材料", "两方披露", "两个说法",
    "这两个来源", "官方与第三方", "官网与监管文件",
])
def test_chinese_collective_accounts_need_a_relation(sources):
    classifier = ResearchTaskClassifier()
    result = classifier.classify(f"核查{sources}对同一次收购的日期是否一致。")
    assert result.category is CONFLICT
    assert "source_account_consistency" in result.matched_signal_codes
    assert classifier.classify(f"核查{sources}是否已经发布。").category is FACTUAL
