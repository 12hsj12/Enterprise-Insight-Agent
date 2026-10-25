# Calibration case selection

Status: SELECTED; report material not yet verified. Human review: PENDING.

Benchmark/rubric: `enterprise-insight-bench-v2/2.2.0`
Dataset SHA-256: `95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`
Cutoff: `2026-09-05`
Source HEAD: `6f457b11a24c9b0a3eefe46559f737390b06f7f5`

These six IDs were recorded before reading any report or starting execution. Selection uses development Required Units and evidence-strength/risk coverage only; no model score was consulted.

| Category | All eligible development IDs | Selected ID | Rationale |
|---|---|---|---|
| factual_verification | EIV2_FV_001, EIV2_FV_002, EIV2_FV_003 | EIV2_FV_001 | Default versus exceptions and retention: status, conflict, numeric and time scope. |
| technical_capability_analysis | EIV2_TC_001, EIV2_TC_002, EIV2_TC_003 | EIV2_TC_001 | Hybrid retrieval and index tradeoffs: primary plus independent evidence, comparison and performance. |
| competitive_comparison | EIV2_CC_001, EIV2_CC_002, EIV2_CC_003 | EIV2_CC_001 | Per-entity comparable primary evidence, availability and numeric pricing; strict freshness. |
| trend_market_intelligence | EIV2_TM_001, EIV2_TM_002, EIV2_TM_003 | EIV2_TM_003 | Regional expansion, model diversity and enterprise controls; strict 180-day freshness and independent sources. |
| conflict_credibility_resolution | EIV2_CR_001, EIV2_CR_002, EIV2_CR_003 | EIV2_CR_003 | Vendor benchmark versus replication: numerical performance, setup comparability and conflict adjudication. |
| enterprise_decision_recommendation | EIV2_ED_001, EIV2_ED_002, EIV2_ED_003 | EIV2_ED_002 | Separate factual capability/performance premises from conditional migration recommendations. |

## Planned coverage versus observed coverage

Selected Required Units name six risk types: numeric_value, date_or_time_window, release_status_availability, comparative_claim, benchmark_or_performance, conflict_sensitive_claim. This is planned coverage, not a finding about report claims. No development Required Unit explicitly names market_metric or superlative_or_ranking; do not fabricate claims to fill these gaps. Actual report coverage must be recorded after real report material is available.

Only development records were emitted from dataset parsing. Holdout records were not displayed, selected, reviewed or annotated.
