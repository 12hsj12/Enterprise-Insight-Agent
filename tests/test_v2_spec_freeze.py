import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json"
ARCHITECTURE = ROOT / "docs/v2/V2_ARCHITECTURE_SPEC.md"
BENCHMARK = ROOT / "docs/v2/V2_BENCHMARK_SPEC.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_dataset_is_frozen_and_stratified():
    data = load(DATASET)
    assert data["status"] == "FROZEN"
    assert data["schema_version"] == "enterprise-insight-bench-v2/2.0.0"
    cases = data["cases"]
    assert len(cases) == 30
    assert len({case["id"] for case in cases}) == 30
    assert Counter(case["split"] for case in cases) == {"development": 18, "holdout": 12}
    by_category = defaultdict(Counter)
    for case in cases:
        by_category[case["category"]][case["split"]] += 1
        assert case["cutoff_date"] == data["cutoff_date"]
        assert len(case["required_units"]) >= 3
        assert len({unit["id"] for unit in case["required_units"]}) == len(case["required_units"])
        for unit in case["required_units"]:
            assert unit["evidence_strength_rule"]
            assert isinstance(unit["high_risk_types"], list)
    assert set(by_category) == set(data["categories"])
    assert all(counts == {"development": 3, "holdout": 2} for counts in by_category.values())


def test_policy_and_acceptance_contract_is_complete():
    data = load(DATASET)
    assert set(data["evidence_policies"]) == set(data["categories"])
    expected_weights = {
        "factual_verification": 0.30,
        "technical_capability_analysis": 0.22,
        "competitive_comparison": 0.10,
        "trend_market_intelligence": 0.12,
        "conflict_credibility_resolution": 0.18,
        "enterprise_decision_recommendation": 0.08,
    }
    for category, policy in data["evidence_policies"].items():
        assert policy["authority_weight"] == expected_weights[category]
        assert policy["authority_weight"] < 0.5
        assert policy["preferred_source_types"]
        assert policy["freshness_mode"] in {"not_required", "contextual", "strict"}
        assert policy["corroboration_rule"]
        assert policy["primary_source_rule"]
        assert policy["independent_source_rule"] == "publisher_organization"
        assert policy["corroboration_rule"] in data["claim_gate_rules"]["strength_rules"]
    gate = data["claim_gate_rules"]
    assert gate["default_non_required_unit_rule"] == "standard"
    assert gate["required_unit_combination"] == "union_without_weakening"
    assert gate["multi_risk_combination"] == "union_without_weakening"
    assert gate["risk_to_minimum_rule"] == {
        "numeric_value": "primary_or_two_independent",
        "date_or_time_window": "primary_or_two_independent",
        "release_status_availability": "primary_or_two_independent",
        "comparative_claim": "two_independent",
        "superlative_or_ranking": "two_independent",
        "market_metric": "primary_or_two_independent",
        "benchmark_or_performance": "primary_plus_independent",
        "conflict_sensitive_claim": "conflict_sides_plus_adjudicator",
    }
    assert set(gate["risk_to_minimum_rule"].values()) <= set(gate["strength_rules"])
    assert gate["comparison_primary_override"] == "comparable_primary_evidence_per_entity"
    reliability = data["metric_contracts"]["source_reliability_score"]
    assert reliability == {
        "unit": "distinct_normalized_supporting_source_per_report",
        "deduplicate_chunks_and_links": True,
        "exclude_relations": ["conflict", "unclear", "unused"],
    }
    acceptance = data["acceptance_criteria"]
    required = {
        "minimum_improved_core_metrics_vs_baseline",
        "remaining_metric_max_regression_pp",
        "severe_category_regression_pp",
        "classification_accuracy_min",
        "generalization_gap_rule",
        "absolute_quality_floor",
    }
    assert required <= set(acceptance)
    assert acceptance["minimum_improved_core_metrics_vs_baseline"] == 4
    assert acceptance["citation_correctness"] == "v2 > baseline"
    assert acceptance["citation_completeness"] == "v2 >= baseline"
    assert acceptance["strong_evidence_coverage"] == "v2 > baseline"
    assert acceptance["source_reliability_score"] == "v2 > baseline"
    assert acceptance["high_risk_claim_corroboration_rate"] == "v2 > baseline"
    assert acceptance["remaining_metric_max_regression_pp"] == 1.0
    assert acceptance["severe_category_regression_pp"] == 5.0
    assert acceptance["generalization_gap_rule"] == "mean_abs_gap_v2 <= mean_abs_gap_baseline - 0.01"
    assert acceptance["absolute_quality_floor"] == {
        "citation_correctness": 0.9,
        "citation_completeness": 0.97,
        "strong_evidence_coverage": 0.85,
        "source_reliability_score": 0.75,
        "high_risk_claim_corroboration_rate": 0.9,
    }


def test_frozen_docs_cover_required_semantics():
    text = (ARCHITECTURE.read_text(encoding="utf-8") + BENCHMARK.read_text(encoding="utf-8")).lower()
    for phrase in (
        "authority_score", "source-level reliability prior", "claim gate", "grounding validation",
        "required unit", "strong evidence coverage", "source reliability score",
        "high-risk claim corroboration rate", "task classification accuracy",
        "category robustness", "generalization gap", "paired candidate", "baseline", "v1", "v2",
    ):
        assert phrase in text
