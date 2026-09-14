# V2.2.0 Development Failure Map

This map freezes the human-reviewed development baseline before any bounded utility correction. It is an evidence-based mapping artifact, not a feature implementation or a claim that the system failed on holdout.

## Scope and semantics

- Benchmark schema: `enterprise-insight-bench-v2/2.2.0`
- Dataset SHA-256: `95a9718c7e16b5a5c1ee966ee89e217aba0b0368b6e6afc4cd7c5d6a071896fa`
- Information cutoff: `2026-09-05`
- Source commit before freeze: `392f6e46ca7de753e39913326c035233488ad8bf`
- Required Units: 18; final human result: 1 SATISFIED / 17 NOT_SATISFIED
- `final_report_coverage`: `full` means substantive report coverage, `partial` means related content misses an obligation, and `none` means no emitted report claim.
- `independent_source_count` is a deduplicated saved-source diagnostic. Repeated chunks and URL variants are collapsed; distinct URLs do not automatically prove independent publisher organizations.
- `verified` in freshness metadata means the publication date itself was verified. It does not automatically mean the frozen age window was satisfied.

## Required Unit records

| Case | Category | Required Unit | Human | Report coverage | Evidence | Primary | Independent source count | Freshness | Gate effect | Dominant failure |
|---|---|---|---|---|---:|---:|---:|---|---|---|
| EIV2_CC_001 | competitive_comparison | 模型选择对比 | NOT_SATISFIED | none | True | False | 1 | unverified | omit/no_claims_emitted | SAFE_ABSTENTION |
| EIV2_CC_001 | competitive_comparison | 治理与网络隔离对比 | NOT_SATISFIED | none | True | False | 1 | unverified | omit/no_claims_emitted | SAFE_ABSTENTION |
| EIV2_CC_001 | competitive_comparison | 定价透明度对比 | NOT_SATISFIED | none | True | False | 1 | unverified | omit/no_claims_emitted | SAFE_ABSTENTION |
| EIV2_CR_003 | conflict_credibility_resolution | 厂商报告分数 | NOT_SATISFIED | none | True | True | 1 | not_required | omit/no_claims_emitted | SAFE_ABSTENTION |
| EIV2_CR_003 | conflict_credibility_resolution | 第三方复现结果 | NOT_SATISFIED | none | True | False | 1 | not_required | omit/no_claims_emitted | SAFE_ABSTENTION |
| EIV2_CR_003 | conflict_credibility_resolution | 差异解释与可信判断 | NOT_SATISFIED | none | True | True | 2 | not_required | omit/no_claims_emitted | SAFE_ABSTENTION |
| EIV2_ED_002 | enterprise_decision_recommendation | 候选技术能力 | NOT_SATISFIED | partial | True | True | 2 | not_required | emit | TASK_COVERAGE_FAILURE |
| EIV2_ED_002 | enterprise_decision_recommendation | 规模与运维条件 | NOT_SATISFIED | partial | True | False | 1 | not_required | emit | EVIDENCE_STRENGTH_FAILURE |
| EIV2_ED_002 | enterprise_decision_recommendation | 条件化迁移建议 | NOT_SATISFIED | partial | True | False | 1 | unverified | emit | TASK_COVERAGE_FAILURE |
| EIV2_FV_001 | factual_verification | 默认训练用途政策 | SATISFIED | full | True | True | 3 | not_required | hedge | NO_FAILURE |
| EIV2_FV_001 | factual_verification | 明确适用例外 | NOT_SATISFIED | partial | True | False | 3 | not_required | hedge | EVIDENCE_STRENGTH_FAILURE |
| EIV2_FV_001 | factual_verification | 数据保留或控制边界 | NOT_SATISFIED | partial | True | True | 1 | unverified | emit | TASK_COVERAGE_FAILURE |
| EIV2_TC_001 | technical_capability_analysis | 混合检索机制 | NOT_SATISFIED | full | True | False | 2 | not_required | emit | PRIMARY_SOURCE_GAP |
| EIV2_TC_001 | technical_capability_analysis | 索引选择与权衡 | NOT_SATISFIED | partial | True | False | 2 | not_required | emit | TASK_COVERAGE_FAILURE |
| EIV2_TC_001 | technical_capability_analysis | 企业工作负载限制 | NOT_SATISFIED | full | True | False | 2 | not_required | emit | INDEPENDENCE_GAP |
| EIV2_TM_003 | trend_market_intelligence | 区域扩张趋势 | NOT_SATISFIED | partial | True | False | 1 | unverified | emit | INDEPENDENCE_GAP |
| EIV2_TM_003 | trend_market_intelligence | 模型多样化趋势 | NOT_SATISFIED | partial | True | False | 1 | unverified | emit | INDEPENDENCE_GAP |
| EIV2_TM_003 | trend_market_intelligence | 企业控制趋势 | NOT_SATISFIED | partial | True | True | 2 | unverified | emit | FRESHNESS_GAP |

### Evidence-based rationale

#### EIV2_CC_001 / model_choice — 模型选择对比

- Dominant: `SAFE_ABSTENTION`
- Secondary: `EVIDENCE_STRENGTH_FAILURE`, `PRIMARY_SOURCE_GAP`, `INDEPENDENCE_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告只有固定的无断言说明；Gate 因比较所需 two_independent 与每个实体的 comparable primary 未满足而 omit，selected evidence 仅用于解释省略原因。

#### EIV2_CC_001 / governance_network — 治理与网络隔离对比

- Dominant: `SAFE_ABSTENTION`
- Secondary: `EVIDENCE_STRENGTH_FAILURE`, `PRIMARY_SOURCE_GAP`, `INDEPENDENCE_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告没有治理或网络隔离比较内容；Gate/grounding artifacts 显示没有可发出的 claims，保存的第三方材料未满足比较来源义务。

#### EIV2_CC_001 / pricing — 定价透明度对比

- Dominant: `SAFE_ABSTENTION`
- Secondary: `EVIDENCE_STRENGTH_FAILURE`, `PRIMARY_SOURCE_GAP`, `INDEPENDENCE_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告没有定价透明度比较内容；Gate 对比较实体的一手来源与独立支持要求均未满足，因此没有 emitted claim 可覆盖该 Required Unit。

#### EIV2_CR_003 / vendor_score — 厂商报告分数

- Dominant: `SAFE_ABSTENTION`
- Secondary: `EVIDENCE_STRENGTH_FAILURE`, `EVIDENCE_SCOPE_MISMATCH`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告没有 emitted claim；保存材料中虽有 DeepSeek 官方项目来源，但分数需要更完整的厂商结果与冻结强度规则，Gate 因义务未满足而 omit。

#### EIV2_CR_003 / replication — 第三方复现结果

- Dominant: `SAFE_ABSTENTION`
- Secondary: `EVIDENCE_SCOPE_MISMATCH`, `EVIDENCE_STRENGTH_FAILURE`, `INDEPENDENCE_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告没有 emitted claim；HF discussion 讨论的是 DeepScaleR-1.5B-Preview，不能直接替代目标完整 DeepSeek-R1 的第三方复现结果。

#### EIV2_CR_003 / explanation — 差异解释与可信判断

- Dominant: `SAFE_ABSTENTION`
- Secondary: `EVIDENCE_SCOPE_MISMATCH`, `EVIDENCE_STRENGTH_FAILURE`, `INDEPENDENCE_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告没有 emitted claim；保存材料包含官方 R1 项目与 DeepScaleR 讨论，但对象/版本范围不一致，不能直接形成差异解释与可信判断。

#### EIV2_ED_002 / capabilities — 候选技术能力

- Dominant: `TASK_COVERAGE_FAILURE`
- Secondary: `GENERATION_ALIGNMENT_FAILURE`, `EVIDENCE_SCOPE_MISMATCH`, `INDEPENDENCE_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告主要解释 pgvector 的定义与能力，没有围绕托管向量库和搜索引擎候选集合完成对比；已有材料不足以补齐未生成的候选侧内容。

#### EIV2_ED_002 / operations — 规模与运维条件

- Dominant: `EVIDENCE_STRENGTH_FAILURE`
- Secondary: `INDEPENDENCE_GAP`, `TASK_COVERAGE_FAILURE`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告发出 Milvus 部署和 pgvector 运维相关内容，但主要运维比较来自同一社区文章，未建立 two_independent，规模与版本边界也不完整。

#### EIV2_ED_002 / migration — 条件化迁移建议

- Dominant: `TASK_COVERAGE_FAILURE`
- Secondary: `GENERATION_ALIGNMENT_FAILURE`, `EVIDENCE_SCOPE_MISMATCH`, `FRESHNESS_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 最终报告只给出按向量规模、查询模式和架构偏好的选型原则，没有给中型制造企业的条件化迁移步骤或边界；关联 CSDN 材料的日期归属仍有疑点。

#### EIV2_FV_001 / training_default — 默认训练用途政策

- Dominant: `NO_FAILURE`
- Secondary: none
- Reason: 人审接受该条报告中的限定性边界表述；保存的官方政策片段支持默认不训练规则，因此 UNCERTAIN 被覆盖为 SATISFIED。

#### EIV2_FV_001 / exceptions — 明确适用例外

- Dominant: `EVIDENCE_STRENGTH_FAILURE`
- Secondary: `PRIMARY_SOURCE_GAP`, `INDEPENDENCE_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告只保留社区帖子提出的去标识化/匿名化例外争议，并明确标为未确认；保存材料未形成该例外的合格一手或足够独立支持。

#### EIV2_FV_001 / retention — 数据保留或控制边界

- Dominant: `TASK_COVERAGE_FAILURE`
- Secondary: `EVIDENCE_SCOPE_MISMATCH`, `EVIDENCE_STRENGTH_FAILURE`, `FRESHNESS_GAP`
- Reason: 最终报告只说明滥用监控日志和应用状态等存储类型，没有覆盖保留期限、删除或控制边界；唯一关联证据的 publication_date 仍为空。

#### EIV2_TC_001 / hybrid — 混合检索机制

- Dominant: `PRIMARY_SOURCE_GAP`
- Secondary: `INDEPENDENCE_GAP`, `EVIDENCE_STRENGTH_FAILURE`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告清楚描述向量相似度与关键词/元数据过滤的混合机制，但保存引用是教程/文章组合，未建立 pgvector 一手材料加独立佐证。

#### EIV2_TC_001 / indexes — 索引选择与权衡

- Dominant: `TASK_COVERAGE_FAILURE`
- Secondary: `PRIMARY_SOURCE_GAP`, `EVIDENCE_STRENGTH_FAILURE`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告相关段落只说明查询规划器可以使用索引和 SQL 组合，没有组织 HNSW/IVFFlat 的选择与权衡；相关证据也不是目标产品的一手文档。

#### EIV2_TC_001 / limits — 企业工作负载限制

- Dominant: `INDEPENDENCE_GAP`
- Secondary: `EVIDENCE_STRENGTH_FAILURE`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告给出多项生产限制，但两条 VeloDB 证据属于同一页面，另一条 ParadeDB 文章未提供足以完成冻结 two_independent obligation 的资格化元数据。

#### EIV2_TM_003 / regions — 区域扩张趋势

- Dominant: `INDEPENDENCE_GAP`
- Secondary: `EVIDENCE_STRENGTH_FAILURE`, `TASK_COVERAGE_FAILURE`, `FRESHNESS_GAP`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告写到主权云与区域基础设施趋势，但两个关联片段是同一 InfotechLead/ABI Research 报道的 URL 变体，且未完整比较主要云厂商服务的区域扩张；strict freshness 也未资格化。

#### EIV2_TM_003 / models — 模型多样化趋势

- Dominant: `INDEPENDENCE_GAP`
- Secondary: `FRESHNESS_GAP`, `EVIDENCE_STRENGTH_FAILURE`, `TASK_COVERAGE_FAILURE`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告提供模型接入清单，但两个引用来自同一 Bits Lovers 页面，publication_date 未验证，未形成 two_independent 的时效趋势证据。

#### EIV2_TM_003 / controls — 企业控制趋势

- Dominant: `FRESHNESS_GAP`
- Secondary: `TASK_COVERAGE_FAILURE`, `EVIDENCE_STRENGTH_FAILURE`, `QUALIFICATION_METADATA_GAP`
- Reason: 报告同时引用 AWS 治理建议与 Clarip 产品描述，但没有完整建立主要云厂商控制能力的发展趋势，且 strict freshness 证据未确认。

## Summary

### Dominant failure distribution

- `EVIDENCE_STRENGTH_FAILURE`: 2
- `FRESHNESS_GAP`: 1
- `INDEPENDENCE_GAP`: 3
- `PRIMARY_SOURCE_GAP`: 1
- `SAFE_ABSTENTION`: 6
- `TASK_COVERAGE_FAILURE`: 4
- `NO_FAILURE` (the one human-satisfied RU): 1

### Category distribution

- `competitive_comparison`: `SAFE_ABSTENTION`=3
- `conflict_credibility_resolution`: `SAFE_ABSTENTION`=3
- `enterprise_decision_recommendation`: `EVIDENCE_STRENGTH_FAILURE`=1, `TASK_COVERAGE_FAILURE`=2
- `factual_verification`: `EVIDENCE_STRENGTH_FAILURE`=1, `NO_FAILURE`=1, `TASK_COVERAGE_FAILURE`=1
- `technical_capability_analysis`: `INDEPENDENCE_GAP`=1, `PRIMARY_SOURCE_GAP`=1, `TASK_COVERAGE_FAILURE`=1
- `trend_market_intelligence`: `FRESHNESS_GAP`=1, `INDEPENDENCE_GAP`=2

### Planned utility-correction mapping

#### requirement-driven research/generation

- Failure types: `TASK_COVERAGE_FAILURE`, `GENERATION_ALIGNMENT_FAILURE`
- Required Units: `EIV2_FV_001/retention`, `EIV2_TC_001/indexes`, `EIV2_TM_003/regions`, `EIV2_TM_003/controls`, `EIV2_ED_002/capabilities`, `EIV2_ED_002/migration`
- Scope: mapping only; feature not implemented in Batch 0

#### source/date metadata enrichment

- Failure types: `PRIMARY_SOURCE_GAP`, `QUALIFICATION_METADATA_GAP`, `FRESHNESS_GAP`
- Required Units: `EIV2_FV_001/exceptions`, `EIV2_FV_001/retention`, `EIV2_TC_001/hybrid`, `EIV2_TC_001/indexes`, `EIV2_TC_001/limits`, `EIV2_CC_001/model_choice`, `EIV2_CC_001/governance_network`, `EIV2_CC_001/pricing`, `EIV2_TM_003/regions`, `EIV2_TM_003/models`, `EIV2_TM_003/controls`, `EIV2_ED_002/migration`
- Scope: mapping only; feature not implemented in Batch 0

#### one bounded evidence-gap retrieval

- Failure types: `EVIDENCE_STRENGTH_FAILURE`, `PRIMARY_SOURCE_GAP`, `INDEPENDENCE_GAP`, `FRESHNESS_GAP`, `EVIDENCE_SCOPE_MISMATCH`
- Required Units: `EIV2_FV_001/exceptions`, `EIV2_FV_001/retention`, `EIV2_TC_001/hybrid`, `EIV2_TC_001/indexes`, `EIV2_TC_001/limits`, `EIV2_CC_001/model_choice`, `EIV2_CC_001/governance_network`, `EIV2_CC_001/pricing`, `EIV2_TM_003/regions`, `EIV2_TM_003/models`, `EIV2_TM_003/controls`, `EIV2_CR_003/vendor_score`, `EIV2_CR_003/replication`, `EIV2_CR_003/explanation`, `EIV2_ED_002/operations`
- Scope: mapping only; feature not implemented in Batch 0

#### layered evidence disclosure + evidence-grounded AI inference

- Failure types: `SAFE_ABSTENTION`, `GENERATION_ALIGNMENT_FAILURE`, `EVIDENCE_SCOPE_MISMATCH`
- Required Units: `EIV2_CC_001/model_choice`, `EIV2_CC_001/governance_network`, `EIV2_CC_001/pricing`, `EIV2_CR_003/vendor_score`, `EIV2_CR_003/replication`, `EIV2_CR_003/explanation`, `EIV2_ED_002/capabilities`, `EIV2_ED_002/migration`
- Scope: mapping only; feature not implemented in Batch 0

## Integrity boundary

This artifact uses only saved development reports, selected evidence, execution Gate/Grounding artifacts, and the frozen calibration records. It does not inspect or execute holdout cases, call providers, change the rubric, or implement any of the four work packages.
