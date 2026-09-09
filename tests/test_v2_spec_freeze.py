import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "benchmarks/dataset/enterprise_insight_bench_v2.json"
ARCHITECTURE = ROOT / "docs/v2/V2_ARCHITECTURE_SPEC.md"
BENCHMARK = ROOT / "docs/v2/V2_BENCHMARK_SPEC.md"
CHANGE_NOTE = ROOT / "docs/v2/V2_1_ARCHITECTURE_CHANGE_NOTE.md"

ARCHITECTURE_VERSION = "enterprise-insight-v2-architecture/2.1.0"
BENCHMARK_VERSION = "enterprise-insight-bench-v2/2.1.0"
RESOLVER_VERSION = "enterprise-insight-policy-resolver/1.0.0"
DATASET_SHA256 = "956519ed56ecabdba6c8e3ad059b48785772be9b63e1a937485433a204cc3dd5"

# Canonical JSON hashes captured from the required V2.0 revision baseline:
# b0caaed358dbb2d5f3972041c73586055b30d2d7. They make preservation
# independently testable without requiring a .git directory at test time.
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
EXPECTED_ROUTING_MODES = ["single", "multi_policy", "broad_fallback"]
EXPECTED_BROAD_FALLBACK_ORDER = [
    "technical_capability_analysis",
    "factual_verification",
    "competitive_comparison",
    "trend_market_intelligence",
    "conflict_credibility_resolution",
    "enterprise_decision_recommendation",
]


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


def test_v21_versions_and_dataset_byte_hash_are_frozen():
    data = load(DATASET)
    architecture = ARCHITECTURE.read_text(encoding="utf-8")
    benchmark = BENCHMARK.read_text(encoding="utf-8")
    change_note = CHANGE_NOTE.read_text(encoding="utf-8")

    assert data["status"] == "FROZEN"
    assert data["schema_version"] == BENCHMARK_VERSION
    assert ARCHITECTURE_VERSION in architecture
    assert BENCHMARK_VERSION in benchmark
    assert RESOLVER_VERSION in architecture
    assert RESOLVER_VERSION in benchmark
    assert ARCHITECTURE_VERSION in change_note
    assert BENCHMARK_VERSION in change_note
    assert RESOLVER_VERSION in change_note
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == DATASET_SHA256
    assert DATASET_SHA256 in benchmark
    assert DATASET_SHA256 in change_note


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


def test_policy_and_acceptance_contract_is_complete_and_unchanged():
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
    assert gate["comparison_primary_override"] == (
        "comparable_primary_evidence_per_entity"
    )

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


def test_policy_resolver_and_routing_modes_are_frozen():
    routing = load(DATASET)["policy_routing_contract"]
    assert routing["resolver_version"] == RESOLVER_VERSION
    assert routing["routing_modes"] == EXPECTED_ROUTING_MODES
    assert routing["max_policy_branches"] == 3
    assert routing["candidate_categories"] == {
        "type": "unique_ordered_research_task_categories",
        "primary_required_unless_invalid_typed_classification": True,
        "ordering": "primary_then_deterministic_runner_ups",
    }
    assert routing["single_rule"] == (
        "valid_typed_classification_without_fallback_or_material_runner_up"
    )
    assert routing["multi_policy_rule"] == (
        "primary_plus_at_most_two_material_runner_ups"
    )
    assert routing["broad_fallback"] == {
        "triggers": ["classifier_fallback_used", "invalid_typed_classification"],
        "classifier_diagnostic_fallback": "technical_capability_analysis",
        "candidate_categories": EXPECTED_BROAD_FALLBACK_ORDER,
        "observable": True,
    }


def test_shared_pool_fusion_and_claim_safety_contracts_are_frozen():
    routing = load(DATASET)["policy_routing_contract"]
    assert routing["shared_candidate_pool"] == {
        "retrieval_count_per_request": 1,
        "semantic_eligibility_before_policy_reranking": True,
        "policy_branches_use_same_immutable_pool": True,
        "multi_policy_must_not_multiply_live_retrieval": True,
    }
    assert routing["fusion"] == {
        "algorithm": "deterministic_round_robin",
        "branch_order": "primary_then_resolver_candidate_order",
        "deduplicate_by": "evidence_id",
        "stop_rule": "max_results_or_all_branch_views_exhausted",
        "stable_tie_break": "existing_stable_order_then_evidence_id",
    }
    assert routing["policy_obligations"] == [
        "freshness_requirement",
        "preferred_source_roles",
        "corroboration_rule",
        "primary_source_rule",
        "independence_rule",
        "comparison_symmetry",
        "conflict_side_preservation_adjudication",
    ]
    assert routing["claim_minimums"] == (
        "classifier_independent_union_without_weakening"
    )
    assert routing["retrieve_more_driver"] == (
        "unmet_named_claim_or_policy_obligations"
    )
    assert routing["information_cutoff_unconditional"] is True


def test_routing_diagnostics_are_non_headline_and_do_not_replace_accuracy():
    diagnostics = load(DATASET)["routing_diagnostic_contracts"]
    assert diagnostics["policy_candidate_recall"] == (
        "cases_frozen_category_in_candidate_categories/cases_with_routing_decision"
    )
    assert diagnostics["headline"] is False
    assert diagnostics["additional_diagnostics"] == [
        "ambiguity_rate",
        "broad_fallback_rate",
        "mean_resolved_policy_count",
        "maximum_resolved_policy_count",
        "routing_mode_by_frozen_and_predicted_category",
        "policy_obligation_preservation",
        "evidence_overlap_across_policy_branches_optional",
        "local_policy_fusion_latency",
    ]
    assert diagnostics["policy_obligation_preservation"] == (
        "resolver_and_fusion_must_not_silently_discard_named_obligations"
    )

    benchmark = " ".join(BENCHMARK.read_text(encoding="utf-8").lower().split())
    assert "policy candidate recall" in benchmark
    assert "cannot substitute for task classification accuracy" in benchmark
    assert "primary predicted category == frozen category" in benchmark


def test_frozen_docs_cover_required_semantics_and_core_metrics():
    text = " ".join(
        (
            ARCHITECTURE.read_text(encoding="utf-8")
            + BENCHMARK.read_text(encoding="utf-8")
        )
        .lower()
        .split()
    )
    for phrase in (
        "authority_score",
        "source-level reliability prior",
        "policyresolver",
        "policyroutingdecision",
        "single",
        "multi_policy",
        "broad_fallback",
        "shared semantic candidate pool",
        "deterministic round-robin",
        "classifier-independent",
        "union_without_weakening",
        "policy candidate recall",
        "policy obligation preservation",
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
        "paired candidate",
        "baseline",
        "v1",
        "v2",
    ):
        assert phrase in text

    assert "task classification accuracy" in text
    assert "candidate-set membership does not redefine" in text
    assert "must not trigger multiple live searches" in text
    assert "cannot weaken claim-level minimum evidence rules" in text
