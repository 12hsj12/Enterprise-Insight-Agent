import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json"
ARCHITECTURE = ROOT / "docs/v2/V2_ARCHITECTURE_SPEC.md"
BENCHMARK = ROOT / "docs/v2/V2_BENCHMARK_SPEC.md"
V21_CHANGE_NOTE = ROOT / "docs/v2/V2_1_ARCHITECTURE_CHANGE_NOTE.md"
V22_CHANGE_NOTE = ROOT / "docs/v2/V2_2_ARCHITECTURE_CHANGE_NOTE.md"

ARCHITECTURE_VERSION = "enterprise-insight-v2-architecture/2.2.0"
BENCHMARK_VERSION = "enterprise-insight-bench-v2/2.2.0"
CLASSIFIER_VERSION = "enterprise-insight-task-classifier/1.1.0"
DATASET_SHA256 = "95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa"

# Canonical hashes captured from the V2.0 freeze. These independently prove
# that V2.2 changed metadata/scope only, not benchmark semantics.
V20_IMMUTABLE_SECTION_SHA256 = {
    "cutoff_date": "fcd1b035a403732fcb30948679a11651f4a5fb3c2f89fea3e4f990b7deb3db29",
    "categories": "4b01f0e418b0fee8be0a39a3ab7056c6da63b279984160561038e92b34656442",
    "claim_gate_rules": "c3a3cccaa34e86a1b09658ec202a02e68bfe43f941257e766332c70f2fd2d1f9",
    "evidence_policies": "69ee932ac1915f5ef561b35377870b64af10af370661cdfef156229a60a901d4",
    "acceptance_criteria": "cf20780e12f69a341805805d35788e02cd024052630bd4d08864202dc174de3c",
    "metric_contracts": "8c9cae9d798ecd6b4041524b9dd686c61b46e3485554d03c520e8d5224097a4f",
    "cases": "a7533929c245b3146954d0ea2bbb47a602a280c541d33e08cdf1658dfef8e676",
}

EXPECTED_CATEGORIES = [
    "factual_verification",
    "technical_capability_analysis",
    "competitive_comparison",
    "trend_market_intelligence",
    "conflict_credibility_resolution",
    "enterprise_decision_recommendation",
]
EXPECTED_WEIGHTS = {
    "factual_verification": 0.30,
    "technical_capability_analysis": 0.22,
    "competitive_comparison": 0.10,
    "trend_market_intelligence": 0.12,
    "conflict_credibility_resolution": 0.18,
    "enterprise_decision_recommendation": 0.08,
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_v22_versions_and_dataset_byte_hash_are_frozen():
    data = load(DATASET)
    architecture = ARCHITECTURE.read_text(encoding="utf-8")
    benchmark = BENCHMARK.read_text(encoding="utf-8")
    change_note = V22_CHANGE_NOTE.read_text(encoding="utf-8")

    assert data["status"] == "FROZEN"
    assert data["schema_version"] == BENCHMARK_VERSION
    assert data["architecture_version"] == ARCHITECTURE_VERSION
    assert data["classifier_version"] == CLASSIFIER_VERSION
    for text in (architecture, change_note):
        assert ARCHITECTURE_VERSION in text
    for text in (benchmark, change_note):
        assert BENCHMARK_VERSION in text
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == DATASET_SHA256
    assert DATASET_SHA256 in benchmark
    assert DATASET_SHA256 in change_note


def test_historical_v21_change_note_is_retained_and_explicitly_superseded():
    assert V21_CHANGE_NOTE.is_file()
    historical = V21_CHANGE_NOTE.read_text(encoding="utf-8")
    current = V22_CHANGE_NOTE.read_text(encoding="utf-8")
    assert "enterprise-insight-v2-architecture/2.1.0" in historical
    assert "superseded" in current.lower()
    assert V21_CHANGE_NOTE.name in current or "historical V2.1 change note" in current


def test_v20_frozen_benchmark_semantics_are_byte_canonically_preserved():
    data = load(DATASET)
    actual = {
        key: canonical_json_sha256(data[key])
        for key in V20_IMMUTABLE_SECTION_SHA256
    }
    assert actual == V20_IMMUTABLE_SECTION_SHA256


def test_dataset_is_frozen_and_stratified():
    data = load(DATASET)
    assert data["categories"] == EXPECTED_CATEGORIES
    cases = data["cases"]
    assert len(cases) == 30
    assert len({case["id"] for case in cases}) == 30
    assert len({case["query"] for case in cases}) == 30
    assert Counter(case["split"] for case in cases) == {
        "development": 18,
        "holdout": 12,
    }
    by_category = defaultdict(Counter)
    for case in cases:
        by_category[case["category"]][case["split"]] += 1
        assert case["cutoff_date"] == data["cutoff_date"]
        assert len(case["required_units"]) >= 3
        assert len({unit["id"] for unit in case["required_units"]}) == len(
            case["required_units"]
        )
        for unit in case["required_units"]:
            assert unit["evidence_strength_rule"]
            assert isinstance(unit["high_risk_types"], list)
    assert set(by_category) == set(data["categories"])
    assert all(
        counts == {"development": 3, "holdout": 2}
        for counts in by_category.values()
    )


def test_policy_claim_gate_metrics_and_acceptance_are_unchanged():
    data = load(DATASET)
    assert set(data["evidence_policies"]) == set(data["categories"])
    for category, policy in data["evidence_policies"].items():
        assert policy["authority_weight"] == EXPECTED_WEIGHTS[category]
        assert policy["authority_weight"] <= 0.30
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
    assert gate["comparison_primary_override"] == "comparable_primary_evidence_per_entity"

    reliability = data["metric_contracts"]["source_reliability_score"]
    assert reliability == {
        "unit": "distinct_normalized_supporting_source_per_report",
        "deduplicate_chunks_and_links": True,
        "exclude_relations": ["conflict", "unclear", "unused"],
    }

    acceptance = data["acceptance_criteria"]
    assert acceptance["minimum_improved_core_metrics_vs_baseline"] == 4
    assert acceptance["citation_correctness"] == "v2 > baseline"
    assert acceptance["citation_completeness"] == "v2 >= baseline"
    assert acceptance["strong_evidence_coverage"] == "v2 > baseline"
    assert acceptance["source_reliability_score"] == "v2 > baseline"
    assert acceptance["high_risk_claim_corroboration_rate"] == "v2 > baseline"
    assert acceptance["remaining_metric_max_regression_pp"] == 1.0
    assert acceptance["severe_category_regression_pp"] == 5.0
    assert acceptance["classification_accuracy_min"] == 0.9
    assert acceptance["generalization_gap_rule"] == (
        "mean_abs_gap_v2 <= mean_abs_gap_baseline - 0.01"
    )
    assert acceptance["absolute_quality_floor"] == {
        "citation_correctness": 0.9,
        "citation_completeness": 0.97,
        "strong_evidence_coverage": 0.85,
        "source_reliability_score": 0.75,
        "high_risk_claim_corroboration_rate": 0.9,
    }


def test_adaptive_weight_only_runtime_contract_is_frozen():
    contract = load(DATASET)["adaptive_weight_contract"]
    assert contract["runtime_effect"] == "primary_category_selects_authority_weight_only"
    assert contract["runner_up_categories_affect_weight"] is False
    assert contract["confidence_affects_weight"] is False
    assert contract["fallback"] == {
        "triggers": ["classifier_fallback_used", "invalid_or_missing_classification"],
        "diagnostic_primary_category": "technical_capability_analysis",
        "authority_weight": 0.2,
        "observable": True,
    }
    assert contract["semantic_selection"] == {
        "retrieval_count_per_request": 1,
        "semantic_eligibility_before_source_aware_reranking": True,
        "task_classification_must_not_add_retrieval": True,
        "missing_similarity_in_weighted_standard_path": "fail",
    }
    assert contract["scoring"] == {
        "formula": "(1-w)*semantic_similarity+w*authority_score",
        "maximum_authority_weight": 0.3,
        "authority_score_semantics": "source_level_reliability_prior",
    }
    assert contract["evidence_policy_runtime_scope"] == {
        "actively_enforced_field": "authority_weight",
        "other_fields": "metadata_and_downstream_guidance_not_classifier_controlled_hard_rules",
    }
    assert contract["claim_minimums"] == "classifier_independent_union_without_weakening"
    assert "policy_routing_contract" not in load(DATASET)
    assert "routing_diagnostic_contracts" not in load(DATASET)


def test_selection_diagnostics_keep_primary_accuracy_and_no_candidate_recall():
    diagnostics = load(DATASET)["selection_diagnostic_contracts"]
    assert diagnostics["task_classification_accuracy"] == (
        "primary_predicted_category_equals_frozen_category"
    )
    assert diagnostics["fields"] == [
        "primary_category",
        "classifier_confidence",
        "runner_up_categories",
        "signal_codes",
        "rationale_codes",
        "fallback_used",
        "classifier_version",
        "effective_authority_weight",
    ]
    assert diagnostics["headline"] is False
    assert "policy candidate recall" not in BENCHMARK.read_text(encoding="utf-8").lower()


def test_current_docs_freeze_classifier_independent_claim_safety():
    text = " ".join(
        (ARCHITECTURE.read_text(encoding="utf-8") + BENCHMARK.read_text(encoding="utf-8"))
        .lower()
        .split()
    )
    for phrase in (
        "authority_score",
        "source-level reliability prior",
        "semantic candidate eligibility",
        "sourceawarescorer",
        "adaptive authority-weight",
        "fallback",
        "0.20",
        "classifier-independent",
        "union_without_weakening",
        "claim gate",
        "grounding validation",
        "required unit",
        "citation correctness",
        "citation completeness",
        "strong evidence coverage",
        "source reliability score",
        "high-risk claim corroboration rate",
        "task classification accuracy",
        "category robustness",
        "generalization gap",
        "baseline",
        "v1",
        "v2",
    ):
        assert phrase in text
    assert "does not authorize factual claim emission" in text
    assert "cannot weaken" in text
    assert "confidence and runner-up categories do not change the weight" in text


def test_production_source_has_no_abandoned_v21_routing_implementation():
    production_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (ROOT / "gpt_researcher").rglob("*.py")
    ).lower()
    abandoned_symbols = (
        "policyresolver",
        "policyroutingdecision",
        "multi_policy",
        "broad_fallback",
        "deterministic_round_robin",
        "policy_candidate_recall",
        "resolver_version",
        "enterprise-insight-policy-resolver",
    )
    assert all(symbol not in production_text for symbol in abandoned_symbols)
