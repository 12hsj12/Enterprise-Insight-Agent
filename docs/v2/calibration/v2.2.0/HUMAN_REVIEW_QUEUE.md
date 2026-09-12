# V2.2 compressed human review queue

Status: **READY_FOR_HUMAN_REVIEW**. All recommendations remain AI-assisted; all human fields remain unset.

Full ledger: 483; machine-resolved/no-human-action: 227; calibration core: 51; adjudication queue: 36; human workload: 87 tasks.

The 483 original objects are preserved in `FULL_AI_ASSISTED_LEDGER.json`. A task may reference several ledger records when one report sentence controls their shared semantic decision.

## Human calibration core

### CORE-001 — EIV2_FV_001 / required_unit

Ledger: EIV2_FV_001-required_unit-001

Required Unit: 默认训练用途政策

Report passage: 该条款与 API 默认不用于训练或改进的表述之间存在边界争议。

AI recommendation: UNCERTAIN

Reason: 正文仅在被限定的争议句中提到默认不训练；官方片段支持默认规则，但报告缺少直接明确的默认政策陈述。人工裁定该隐含提及是否满足完整 Required Unit，不能自动计分。

Evidence: ev_b08a10e340e4cca0 — https://community.openai.com/t/api-is-our-data-really-ours-major-concern-in-data-processing-addendum/773047 (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/11/content`)
Evidence: ev_d384aee29a4051c8 — https://community.openai.com/t/api-is-our-data-really-ours-major-concern-in-data-processing-addendum/773047 (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/10/content`)
Evidence: ev_d2c625b8589d3de9 — https://openai.xiniushu.com/policies/api-data-usage-policies (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/6/content`)
Evidence: ev_2031367fc36e847d — https://developers.openai.com/api/docs/guides/your-data (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/19/content`)

Human decision: PENDING

### CORE-002 — EIV2_FV_001 / required_unit

Ledger: EIV2_FV_001-required_unit-002

Required Unit: 明确适用例外

Report passage: 社区帖子引用 OpenAI 数据保护附录称,OpenAI 可继续处理源自客户数据的去标识化、匿名化或聚合信息,以改进 OpenAI 的系统和服务

AI recommendation: NOT_SATISFIED

Reason: 报告保留社区争议，没有明确解释已适用的 opt-in 等例外。计划中被 OMIT 的内容不能用于报告覆盖。

Evidence: ev_b08a10e340e4cca0 — https://community.openai.com/t/api-is-our-data-really-ours-major-concern-in-data-processing-addendum/773047 (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/11/content`)
Evidence: ev_d384aee29a4051c8 — https://community.openai.com/t/api-is-our-data-really-ours-major-concern-in-data-processing-addendum/773047 (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/10/content`)
Evidence: ev_d2c625b8589d3de9 — https://openai.xiniushu.com/policies/api-data-usage-policies (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/6/content`)
Evidence: ev_2031367fc36e847d — https://developers.openai.com/api/docs/guides/your-data (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/19/content`)

Human decision: PENDING

### CORE-003 — EIV2_FV_001 / required_unit

Ledger: EIV2_FV_001-required_unit-003

Required Unit: 数据保留或控制边界

Report passage: OpenAI 平台文档称 API 数据可能以滥用监控日志和应用状态形式存储;某些 API 功能会为完成请求或任务而持久化数据。

AI recommendation: NOT_SATISFIED

Reason: 报告解释存储类型但未交代保留期限、删除或控制边界；该片段不足以确认完整边界覆盖。

Evidence: ev_2031367fc36e847d — https://developers.openai.com/api/docs/guides/your-data (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/19/content`)

Human decision: PENDING

### CORE-004 — EIV2_TC_001 / required_unit

Ledger: EIV2_TC_001-required_unit-001

Required Unit: 混合检索机制

Report passage: Hybrid search in pgvector contexts combines vector\-based similarity search with traditional keyword or metadata filtering because vector search handles semantic meaning but can fail on specific keywords or structured constraints\.

AI recommendation: NOT_SATISFIED

Reason: 机制有明确描述，但当前引用未建立 pgvector 项目的一手材料加独立佐证组合；不能用多个教程自动满足 primary_plus_independent。

Evidence: ev_62fa0fb7bbfd9bb8 — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/38/content`)
Evidence: ev_7a6809120ded0e6a — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/32/content`)
Evidence: ev_4426f461ab217c20 — https://medium.com/@aysebilgegunduz/all-you-need-to-know-about-pgvector-part-4-hybrid-search-8a655d3b0087 (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/35/content`)

Human decision: PENDING

### CORE-005 — EIV2_TC_001 / required_unit

Ledger: EIV2_TC_001-required_unit-002

Required Unit: 索引选择与权衡

Report passage: The PostgreSQL query planner can use pgvector indexes for nearest\-neighbor queries, and vector search can be combined with standard SQL filters, joins, and CTEs in the same query\.

AI recommendation: NOT_SATISFIED

Reason: 报告只说规划器可用索引，没有完成 HNSW/IVFFlat 选择与权衡；被 OMIT 的计划内容不能补覆盖。

Evidence: ev_9c01b4455145f8f5 — https://www.tigerdata.com/blog/the-postgres-developers-guide-to-vector-index-tradeoffs (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/7/content`)
Evidence: ev_e38e6e3a23869cb1 — https://www.velodb.io/glossary/what-is-pgvector (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/18/content`)

Human decision: PENDING

### CORE-006 — EIV2_TC_001 / required_unit

Ledger: EIV2_TC_001-required_unit-003

Required Unit: 企业工作负载限制

Report passage: Managing pgvector in production requires PostgreSQL expertise: vacuum operations become more complex with large vector tables, index maintenance requires downtime or careful online rebuilding, monitoring vector\-specific performance requires custom instrumentation, and backup and restore times increase significantly with vector data\.

AI recommendation: UNCERTAIN

Reason: 报告有多项限制但具体断言主要来自同一 VeloDB 页面，ParadeDB 是另一厂商文章；需要逐断言确认独立来源、利益关系和性能风险所需证据。

Evidence: ev_648babff2ebe3058 — https://www.velodb.io/glossary/what-is-pgvector (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/13/content`)
Evidence: ev_24320d0559472fcb — https://www.velodb.io/glossary/what-is-pgvector (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/14/content`)
Evidence: ev_4b2cc9add6171347 — https://www.paradedb.com/learn/postgresql/pgvector-limitations (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/10/content`)

Human decision: PENDING

### CORE-007 — EIV2_CC_001 / required_unit

Ledger: EIV2_CC_001-required_unit-001

Required Unit: 模型选择对比

Report passage: No claims could be emitted from the available structured evidence.

AI recommendation: NOT_SATISFIED

Reason: 执行成功，最终报告仅有未能发出断言的固定说明。没有报告内容覆盖此 Required Unit。附证据用于检查省略原因，绝非该报告的支持引用。

Evidence: ev_f14e2f4e2cc2dac7 — https://www.vitoshainc.com/azure-openai-vs-aws-bedrock-enterprise-implementation-guide (`docs\v2\calibration\v2.2.0\competitive_comparison\EIV2_CC_001\selected.json#/evidences/10/content`)

Human decision: PENDING

### CORE-008 — EIV2_CC_001 / required_unit

Ledger: EIV2_CC_001-required_unit-002

Required Unit: 治理与网络隔离对比

Report passage: No claims could be emitted from the available structured evidence.

AI recommendation: NOT_SATISFIED

Reason: 执行成功，最终报告仅有未能发出断言的固定说明。没有报告内容覆盖此 Required Unit。附证据用于检查省略原因，绝非该报告的支持引用。

Evidence: ev_5c77e2cd82a5f3f3 — https://pronix.ai/resources/compare/bedrock-vs-azure-openai (`docs\v2\calibration\v2.2.0\competitive_comparison\EIV2_CC_001\selected.json#/evidences/20/content`)

Human decision: PENDING

### CORE-009 — EIV2_CC_001 / required_unit

Ledger: EIV2_CC_001-required_unit-003

Required Unit: 定价透明度对比

Report passage: No claims could be emitted from the available structured evidence.

AI recommendation: NOT_SATISFIED

Reason: 执行成功，最终报告仅有未能发出断言的固定说明。没有报告内容覆盖此 Required Unit。附证据用于检查省略原因，绝非该报告的支持引用。

Evidence: ev_5c44f9c31b22f4b9 — https://www.nextgencodingcompany.com/insights/ai-cloud-services-pricing (`docs\v2\calibration\v2.2.0\competitive_comparison\EIV2_CC_001\selected.json#/evidences/7/content`)

Human decision: PENDING

### CORE-010 — EIV2_TM_003 / required_unit

Ledger: EIV2_TM_003-required_unit-001

Required Unit: 区域扩张趋势

Report passage: Asia\-Pacific is also seeing strong growth in sovereign cloud initiatives driven by data residency and cybersecurity requirements\.

AI recommendation: NOT_SATISFIED

Reason: 已写一般主权云/数据中心区域趋势，但这两条实为同一 InfotechLead/ABI Research 报道的 URL 变体；未满足两独立来源，且并未完整比较主要云厂商生成式 AI 服务的区域扩张。

Evidence: ev_ba15efe17df67fc7 — https://infotechlead.com/data-center/global-data-center-market-splits-along-regional-lines-as-aws-microsoft-azure-google-cloud-equinix-drive-growth-95106 (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/13/content`)
Evidence: ev_d804caf04b023668 — https://infotechlead.com/data-center/global-data-center-market-splits-along-regional-lines-as-aws-microsoft-azure-google-cloud-equinix-drive-growth-95106?amp=1 (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/12/content`)

Human decision: PENDING

### CORE-011 — EIV2_TM_003 / required_unit

Ledger: EIV2_TM_003-required_unit-002

Required Unit: 模型多样化趋势

Report passage: Amazon Bedrock is described as allowing Claude, Llama, Mistral, and Nova to be run behind a single API endpoint\.

AI recommendation: NOT_SATISFIED

Reason: 有模型接入清单，主要来自同一 Bits Lovers 页面；日期未验证，strict freshness 与 two_independent 都未建立。

Evidence: ev_bc4bb002e341d18a — https://www.bitslovers.com/bedrock-vs-azure-ai-foundry-vs-vertex-ai (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/25/content`)
Evidence: ev_b7b08374bb8f37a2 — https://www.bitslovers.com/bedrock-vs-azure-ai-foundry-vs-vertex-ai (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/29/content`)

Human decision: PENDING

### CORE-012 — EIV2_TM_003 / required_unit

Ledger: EIV2_TM_003-required_unit-003

Required Unit: 企业控制趋势

Report passage: AWS Prescriptive Guidance recommends a governance framework including compliance monitoring, standardized regulatory documentation, metadata tagging for training data, controls for cross\-border data and service utilization, and regular third\-party audits\.

AI recommendation: NOT_SATISFIED

Reason: 有 AWS 治理建议和 Clarip 产品描述，但没有证实 strict freshness，也未完整建立主要云厂商控制能力的发展趋势。

Evidence: ev_f9d8189e3e096d02 — https://docs.aws.amazon.com/prescriptive-guidance/latest/gen-ai-lifecycle-operational-excellence/prod-monitoring-security.html (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/9/content`)
Evidence: ev_734423ec37023d5b — https://www.clarip.com/privacy/aws-azure-cloud (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/6/content`)

Human decision: PENDING

### CORE-013 — EIV2_CR_003 / required_unit

Ledger: EIV2_CR_003-required_unit-001

Required Unit: 厂商报告分数

Report passage: No claims could be emitted from the available structured evidence.

AI recommendation: NOT_SATISFIED

Reason: 执行成功但最终报告没有发出任何断言；此 Required Unit 在报告中未覆盖。附 selected 材料仅供核查省略/范围问题，不当作报告引用。复现讨论针对 DeepScaleR-1.5B，不可直接代替完整 DeepSeek-R1 的对照结果。

Evidence: ev_bc6de933035ce124 — https://github.com/deepseek-ai/deepseek-r1 (`docs\v2\calibration\v2.2.0\conflict_credibility_resolution\EIV2_CR_003\selected.json#/evidences/31/content`)

Human decision: PENDING

### CORE-014 — EIV2_CR_003 / required_unit

Ledger: EIV2_CR_003-required_unit-002

Required Unit: 第三方复现结果

Report passage: No claims could be emitted from the available structured evidence.

AI recommendation: NOT_SATISFIED

Reason: 执行成功但最终报告没有发出任何断言；此 Required Unit 在报告中未覆盖。附 selected 材料仅供核查省略/范围问题，不当作报告引用。复现讨论针对 DeepScaleR-1.5B，不可直接代替完整 DeepSeek-R1 的对照结果。

Evidence: ev_143f3ca93d7564dd — https://huggingface.co/agentica-org/DeepScaleR-1.5B-Preview/discussions/13 (`docs\v2\calibration\v2.2.0\conflict_credibility_resolution\EIV2_CR_003\selected.json#/evidences/26/content`)

Human decision: PENDING

### CORE-015 — EIV2_CR_003 / required_unit

Ledger: EIV2_CR_003-required_unit-003

Required Unit: 差异解释与可信判断

Report passage: No claims could be emitted from the available structured evidence.

AI recommendation: NOT_SATISFIED

Reason: 执行成功但最终报告没有发出任何断言；此 Required Unit 在报告中未覆盖。附 selected 材料仅供核查省略/范围问题，不当作报告引用。复现讨论针对 DeepScaleR-1.5B，不可直接代替完整 DeepSeek-R1 的对照结果。

Evidence: ev_e453919bda9288fe — https://github.com/deepseek-ai/deepseek-r1 (`docs\v2\calibration\v2.2.0\conflict_credibility_resolution\EIV2_CR_003\selected.json#/evidences/28/content`)
Evidence: ev_143f3ca93d7564dd — https://huggingface.co/agentica-org/DeepScaleR-1.5B-Preview/discussions/13 (`docs\v2\calibration\v2.2.0\conflict_credibility_resolution\EIV2_CR_003\selected.json#/evidences/26/content`)

Human decision: PENDING

### CORE-016 — EIV2_ED_002 / required_unit

Ledger: EIV2_ED_002-required_unit-001

Required Unit: 候选技术能力

Report passage: pgvector 是 PostgreSQL 的开源扩展,用于在关系型数据库中存储、索引和检索向量。

AI recommendation: NOT_SATISFIED

Reason: 正文主要解释 pgvector，未完整覆盖托管向量库和搜索引擎候选能力比较；不能只给 pgvector 定义部分分。

Evidence: ev_da115e732ec66537 — https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/0/content`)
Evidence: ev_c9d5eadb6fa50bc7 — https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/1/content`)
Evidence: ev_00b4876769cb1a7f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/9/content`)

Human decision: PENDING

### CORE-017 — EIV2_ED_002 / required_unit

Ledger: EIV2_ED_002-required_unit-002

Required Unit: 规模与运维条件

Report passage: Milvus 需要 Docker Compose 或 Kubernetes 部署;单机版也需要同时运行 etcd、MinIO 和 Milvus 三个容器;生产集群还需配置 Pulsar 或 Kafka。

AI recommendation: NOT_SATISFIED

Reason: 主要运维比较仅来自同一社区文章；未建立 two_independent，规模条件与版本限制也不足。

Evidence: ev_332ae8b15ef78f5f — https://developer.cloud.tencent.com/article/2658089 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/23/content`)
Evidence: ev_332ae8b15ef78f5f — https://developer.cloud.tencent.com/article/2658089 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/23/content`)

Human decision: PENDING

### CORE-018 — EIV2_ED_002 / required_unit

Ledger: EIV2_ED_002-required_unit-003

Required Unit: 条件化迁移建议

Report passage: 从架构选型看,向量检索不再是单一选型决策,而需根据向量规模、查询模式、架构偏好选择不同方案。

AI recommendation: NOT_SATISFIED

Reason: 仅有按规模/查询模式选型的原则，未给制造企业的条件化迁移步骤或边界；来源日期还有归属疑点。

Evidence: ev_1f4a4d719a744227 — https://blog.csdn.net/afjkdajs/article/details/163944680 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/6/content`)

Human decision: PENDING

### CORE-019 — EIV2_FV_001 / claim_segmentation

Ledger: EIV2_FV_001-C001

Required Unit: not applicable

Report passage: OpenAI 的隐私政策不适用于其代表商业产品客户\(例如 API 服务客户\)处理的内容;此类数据的使用受相关客户协议约束。

AI recommendation: factual

Reason: 分开政策适用范围与客户协议约束两个可核查断言。

Evidence: ev_6f1b032c397627b6 — https://openai.com/zh-Hans-CN/policies/row-privacy-policy (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/1/content`)

Human decision: PENDING

### CORE-020 — EIV2_FV_001 / claim_segmentation

Ledger: EIV2_FV_001-C002

Required Unit: not applicable

Report passage: OpenAI 的隐私政策不适用于其代表商业产品客户\(例如 API 服务客户\)处理的内容;此类数据的使用受相关客户协议约束。

AI recommendation: factual

Reason: 分开政策适用范围与客户协议约束两个可核查断言。

Evidence: ev_6f1b032c397627b6 — https://openai.com/zh-Hans-CN/policies/row-privacy-policy (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/1/content`)

Human decision: PENDING

### CORE-021 — EIV2_FV_001 / citation_support

Ledger: EIV2_FV_001-citation_support-001

Required Unit: not applicable

Report passage: OpenAI 的隐私政策不适用于其代表商业产品客户\(例如 API 服务客户\)处理的内容;此类数据的使用受相关客户协议约束。

AI recommendation: support

Reason: 保存的 OpenAI 隐私政策直接说明商业/API 客户内容的排除范围及客户协议约束。

Evidence: ev_6f1b032c397627b6 — https://openai.com/zh-Hans-CN/policies/row-privacy-policy (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/1/content`)

Human decision: PENDING

### CORE-022 — EIV2_FV_001 / citation_support

Ledger: EIV2_FV_001-citation_support-002

Required Unit: not applicable

Report passage: OpenAI 的隐私政策不适用于其代表商业产品客户\(例如 API 服务客户\)处理的内容;此类数据的使用受相关客户协议约束。

AI recommendation: support

Reason: 保存的 OpenAI 隐私政策直接说明商业/API 客户内容的排除范围及客户协议约束。

Evidence: ev_6f1b032c397627b6 — https://openai.com/zh-Hans-CN/policies/row-privacy-policy (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/1/content`)

Human decision: PENDING

### CORE-023 — EIV2_FV_001 / evidence_strength

Ledger: EIV2_FV_001-evidence_strength-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: PRIMARY

Reason: openai.com 原站标题和以‘我们’说明自身政策的内容一致；只对自身隐私政策一手。

Evidence: ev_6f1b032c397627b6 — https://openai.com/zh-Hans-CN/policies/row-privacy-policy (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/1/content`)

Human decision: PENDING

### CORE-024 — EIV2_FV_001 / independence

Ledger: EIV2_FV_001-independence-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: SAME_SOURCE_GROUP

Reason: 使用内容身份与来源角色建议分组；同一页面的多个 chunk 不重复计为独立来源。不同域名本身不证明独立性。openai.com 原站标题和以‘我们’说明自身政策的内容一致；只对自身隐私政策一手。

Evidence: ev_6f1b032c397627b6 — https://openai.com/zh-Hans-CN/policies/row-privacy-policy (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/1/content`)

Human decision: PENDING

### CORE-025 — EIV2_FV_001 / freshness

Ledger: EIV2_FV_001-freshness-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: verified

Reason: 保存页头明确 Updated 日期，早于截止且在本类别 365 天窗口内。

Evidence: ev_6f1b032c397627b6 — https://openai.com/zh-Hans-CN/policies/row-privacy-policy (`docs\v2\calibration\v2.2.0\factual_verification\EIV2_FV_001\selected.json#/evidences/1/content`)

Human decision: PENDING

### CORE-026 — EIV2_TC_001 / claim_segmentation

Ledger: EIV2_TC_001-C001

Required Unit: not applicable

Report passage: Hybrid search in pgvector contexts combines vector\-based similarity search with traditional keyword or metadata filtering because vector search handles semantic meaning but can fail on specific keywords or structured constraints\.

AI recommendation: factual

Reason: 混合检索组成是一个机制断言。

Evidence: ev_62fa0fb7bbfd9bb8 — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/38/content`)
Evidence: ev_7a6809120ded0e6a — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/32/content`)
Evidence: ev_4426f461ab217c20 — https://medium.com/@aysebilgegunduz/all-you-need-to-know-about-pgvector-part-4-hybrid-search-8a655d3b0087 (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/35/content`)

Human decision: PENDING

### CORE-027 — EIV2_TC_001 / claim_segmentation

Ledger: EIV2_TC_001-C002

Required Unit: not applicable

Report passage: Hybrid search in pgvector contexts combines vector\-based similarity search with traditional keyword or metadata filtering because vector search handles semantic meaning but can fail on specific keywords or structured constraints\.

AI recommendation: factual

Reason: 语义匹配能力与局限分开。

Evidence: ev_62fa0fb7bbfd9bb8 — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/38/content`)
Evidence: ev_7a6809120ded0e6a — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/32/content`)
Evidence: ev_4426f461ab217c20 — https://medium.com/@aysebilgegunduz/all-you-need-to-know-about-pgvector-part-4-hybrid-search-8a655d3b0087 (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/35/content`)

Human decision: PENDING

### CORE-028 — EIV2_TC_001 / citation_support

Ledger: EIV2_TC_001-citation_support-001

Required Unit: not applicable

Report passage: Hybrid search in pgvector contexts combines vector\-based similarity search with traditional keyword or metadata filtering because vector search handles semantic meaning but can fail on specific keywords or structured constraints\.

AI recommendation: support

Reason: 保存片段直接包含此断言的对应机制/用途；不把文中其他未引用断言补入支持。

Evidence: ev_62fa0fb7bbfd9bb8 — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/38/content`)

Human decision: PENDING

### CORE-029 — EIV2_TC_001 / citation_support

Ledger: EIV2_TC_001-citation_support-002

Required Unit: not applicable

Report passage: Hybrid search in pgvector contexts combines vector\-based similarity search with traditional keyword or metadata filtering because vector search handles semantic meaning but can fail on specific keywords or structured constraints\.

AI recommendation: support

Reason: 保存片段直接包含此断言的对应机制/用途；不把文中其他未引用断言补入支持。

Evidence: ev_7a6809120ded0e6a — https://www.instaclustr.com/education/vector-database/pgvector-hybrid-search-benefits-use-cases-and-quick-tutorial (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/32/content`)

Human decision: PENDING

### CORE-030 — EIV2_TC_001 / evidence_strength

Ledger: EIV2_TC_001-evidence_strength-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: PRIMARY_FOR_OWN_OFFERING_ONLY

Reason: 表格明确自身 pgvector on DanubeData；对一般 pgvector 性能不是独立原始测量。

Evidence: ev_16e2a002c3dcd617 — https://danubedata.ro/blog/pgvector-rag-managed-postgres-2026 (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/24/content`)

Human decision: PENDING

### CORE-031 — EIV2_TC_001 / independence

Ledger: EIV2_TC_001-independence-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: SAME_SOURCE_GROUP

Reason: 使用内容身份与来源角色建议分组；同一页面的多个 chunk 不重复计为独立来源。不同域名本身不证明独立性。表格明确自身 pgvector on DanubeData；对一般 pgvector 性能不是独立原始测量。

Evidence: ev_16e2a002c3dcd617 — https://danubedata.ro/blog/pgvector-rag-managed-postgres-2026 (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/24/content`)

Human decision: PENDING

### CORE-032 — EIV2_TC_001 / freshness

Ledger: EIV2_TC_001-freshness-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: verified

Reason: 保存候选页作者 Adrian Silaghi 之后有日期，早于截止。

Evidence: ev_16e2a002c3dcd617 — https://danubedata.ro/blog/pgvector-rag-managed-postgres-2026 (`docs\v2\calibration\v2.2.0\technical_capability_analysis\EIV2_TC_001\selected.json#/evidences/24/content`)

Human decision: PENDING

### CORE-033 — EIV2_CC_001 / evidence_strength

Ledger: EIV2_CC_001-evidence_strength-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: NOT_PRIMARY_FOR_CLOUD_CAPABILITIES

Reason: 来源是第三方实施指南，不是 AWS/Microsoft 的自身产品文档；未展示可检验原始实验。

Evidence: ev_f14e2f4e2cc2dac7 — https://www.vitoshainc.com/azure-openai-vs-aws-bedrock-enterprise-implementation-guide (`docs\v2\calibration\v2.2.0\competitive_comparison\EIV2_CC_001\selected.json#/evidences/10/content`)

Human decision: PENDING

### CORE-034 — EIV2_CC_001 / independence

Ledger: EIV2_CC_001-independence-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: SAME_SOURCE_GROUP

Reason: 使用内容身份与来源角色建议分组；同一页面的多个 chunk 不重复计为独立来源。不同域名本身不证明独立性。来源是第三方实施指南，不是 AWS/Microsoft 的自身产品文档；未展示可检验原始实验。

Evidence: ev_f14e2f4e2cc2dac7 — https://www.vitoshainc.com/azure-openai-vs-aws-bedrock-enterprise-implementation-guide (`docs\v2\calibration\v2.2.0\competitive_comparison\EIV2_CC_001\selected.json#/evidences/10/content`)

Human decision: PENDING

### CORE-035 — EIV2_TM_003 / claim_segmentation

Ledger: EIV2_TM_003-C027

Required Unit: not applicable

Report passage: Stricter energy regulations and grid constraints in Europe are described as pushing hyperscalers toward consolidation and high\-efficiency deployments\.

AI recommendation: factual

Reason: 按并列能力/条件逐项拆分，短片段主语及归因继承 exact_parent_report_text；引述的厂商/作者观点不能升级为已独立验证的规则。

Evidence: ev_66b81b09c02cd2ae — https://infotechlead.com/data-center/global-data-center-market-splits-along-regional-lines-as-aws-microsoft-azure-google-cloud-equinix-drive-growth-95106?amp=1 (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/14/content`)

Human decision: PENDING

### CORE-036 — EIV2_TM_003 / claim_segmentation

Ledger: EIV2_TM_003-C028

Required Unit: not applicable

Report passage: Asia\-Pacific is also seeing strong growth in sovereign cloud initiatives driven by data residency and cybersecurity requirements\.

AI recommendation: factual

Reason: 按并列能力/条件逐项拆分，短片段主语及归因继承 exact_parent_report_text；引述的厂商/作者观点不能升级为已独立验证的规则。

Evidence: ev_ba15efe17df67fc7 — https://infotechlead.com/data-center/global-data-center-market-splits-along-regional-lines-as-aws-microsoft-azure-google-cloud-equinix-drive-growth-95106 (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/13/content`)

Human decision: PENDING

### CORE-037 — EIV2_TM_003 / citation_support

Ledger: EIV2_TM_003-citation_support-001

Required Unit: not applicable

Report passage: US regulators including the SEC and FTC are focusing on regulatory compliance for generative AI, particularly algorithmic bias and financial data transparency\.

AI recommendation: support

Reason: 保存片段直接载明此内容，页面日期可归属且早于 cutoff；支持建议不替代真实性或一手强度审查。

Evidence: ev_0e6422100fea0896 — https://readitquik.com/ai/ai-governance-2026-multi-cloud-compliance-rules (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/0/content`)

Human decision: PENDING

### CORE-038 — EIV2_TM_003 / citation_support

Ledger: EIV2_TM_003-citation_support-002

Required Unit: not applicable

Report passage: US regulators including the SEC and FTC are focusing on regulatory compliance for generative AI, particularly algorithmic bias and financial data transparency\.

AI recommendation: support

Reason: 保存片段直接载明此内容，页面日期可归属且早于 cutoff；支持建议不替代真实性或一手强度审查。

Evidence: ev_0e6422100fea0896 — https://readitquik.com/ai/ai-governance-2026-multi-cloud-compliance-rules (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/0/content`)

Human decision: PENDING

### CORE-039 — EIV2_TM_003 / evidence_strength

Ledger: EIV2_TM_003-evidence_strength-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: NOT_PRIMARY_FOR_REGULATORY_POLICY

Reason: 作者署名文章，未提供 SEC/FTC 原始政策材料。

Evidence: ev_0e6422100fea0896 — https://readitquik.com/ai/ai-governance-2026-multi-cloud-compliance-rules (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/0/content`)

Human decision: PENDING

### CORE-040 — EIV2_TM_003 / independence

Ledger: EIV2_TM_003-independence-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: SAME_SOURCE_GROUP

Reason: 使用内容身份与来源角色建议分组；同一页面的多个 chunk 不重复计为独立来源。不同域名本身不证明独立性。作者署名文章，未提供 SEC/FTC 原始政策材料。

Evidence: ev_0e6422100fea0896 — https://readitquik.com/ai/ai-governance-2026-multi-cloud-compliance-rules (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/0/content`)

Human decision: PENDING

### CORE-041 — EIV2_TM_003 / freshness

Ledger: EIV2_TM_003-freshness-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: verified

Reason: 文首明确日期，距离 cutoff 180 天；可供 strict 180 天边界人工核对。

Evidence: ev_0e6422100fea0896 — https://readitquik.com/ai/ai-governance-2026-multi-cloud-compliance-rules (`docs\v2\calibration\v2.2.0\trend_market_intelligence\EIV2_TM_003\selected.json#/evidences/0/content`)

Human decision: PENDING

### CORE-042 — EIV2_CR_003 / evidence_strength

Ledger: EIV2_CR_003-evidence_strength-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: PRIMARY_FOR_OWN_MODEL_SETTINGS

Reason: 仓库 namespace、项目名及 our models/our setting 第一人称一致，适合自身评测设置；不是独立复现。

Evidence: ev_bc6de933035ce124 — https://github.com/deepseek-ai/deepseek-r1 (`docs\v2\calibration\v2.2.0\conflict_credibility_resolution\EIV2_CR_003\selected.json#/evidences/31/content`)

Human decision: PENDING

### CORE-043 — EIV2_CR_003 / independence

Ledger: EIV2_CR_003-independence-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: SAME_SOURCE_GROUP

Reason: 使用内容身份与来源角色建议分组；同一页面的多个 chunk 不重复计为独立来源。不同域名本身不证明独立性。仓库 namespace、项目名及 our models/our setting 第一人称一致，适合自身评测设置；不是独立复现。

Evidence: ev_bc6de933035ce124 — https://github.com/deepseek-ai/deepseek-r1 (`docs\v2\calibration\v2.2.0\conflict_credibility_resolution\EIV2_CR_003\selected.json#/evidences/31/content`)

Human decision: PENDING

### CORE-044 — EIV2_CR_003 / freshness

Ledger: EIV2_CR_003-freshness-003

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: verified

Reason: 讨论 opened 日期明确，早于 cutoff；超过本类别 365 天指导窗口，模型版本适用性仍须审核。

Evidence: ev_143f3ca93d7564dd — https://huggingface.co/agentica-org/DeepScaleR-1.5B-Preview/discussions/13 (`docs\v2\calibration\v2.2.0\conflict_credibility_resolution\EIV2_CR_003\selected.json#/evidences/26/content`)

Human decision: PENDING

### CORE-045 — EIV2_ED_002 / claim_segmentation

Ledger: EIV2_ED_002-C001

Required Unit: not applicable

Report passage: pgvector 是 PostgreSQL 的开源扩展,用于在关系型数据库中存储、索引和检索向量。

AI recommendation: factual

Reason: 定义与各项向量操作分别核对；短语继承原句关系型数据库/pgvector 主语。

Evidence: ev_da115e732ec66537 — https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/0/content`)
Evidence: ev_c9d5eadb6fa50bc7 — https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/1/content`)
Evidence: ev_00b4876769cb1a7f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/9/content`)

Human decision: PENDING

### CORE-046 — EIV2_ED_002 / claim_segmentation

Ledger: EIV2_ED_002-C005

Required Unit: not applicable

Report passage: pgvector 支持精确和近似最近邻搜索,并支持 vector、halfvec、sparsevec 等向量类型。

AI recommendation: factual

Reason: 搜索模式与各数据类型分别拆分，类型名继承原句支持关系。

Evidence: ev_00b4876769cb1a7f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/9/content`)
Evidence: ev_42ac6ab50515841f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/5/content`)

Human decision: PENDING

### CORE-047 — EIV2_ED_002 / citation_support

Ledger: EIV2_ED_002-citation_support-001

Required Unit: not applicable

Report passage: pgvector 是 PostgreSQL 的开源扩展,用于在关系型数据库中存储、索引和检索向量。

AI recommendation: support

Reason: 保存片段直接支持此原子技术陈述；来源强度、版本与日期在单独条目审核。

Evidence: ev_da115e732ec66537 — https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/0/content`)

Human decision: PENDING

### CORE-048 — EIV2_ED_002 / citation_support

Ledger: EIV2_ED_002-citation_support-003

Required Unit: not applicable

Report passage: pgvector 是 PostgreSQL 的开源扩展,用于在关系型数据库中存储、索引和检索向量。

AI recommendation: support

Reason: 保存片段直接支持此原子技术陈述；来源强度、版本与日期在单独条目审核。

Evidence: ev_00b4876769cb1a7f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/9/content`)

Human decision: PENDING

### CORE-049 — EIV2_ED_002 / evidence_strength

Ledger: EIV2_ED_002-evidence_strength-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: PRIMARY_FOR_TENCENT_DEPLOYMENT

Reason: 原站文档明确腾讯云已预置版本并提供 SQL；对本云产品部署能力是一手，不能据此主张所有版本通用。

Evidence: ev_00b4876769cb1a7f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/9/content`)

Human decision: PENDING

### CORE-050 — EIV2_ED_002 / independence

Ledger: EIV2_ED_002-independence-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: SAME_SOURCE_GROUP

Reason: 使用内容身份与来源角色建议分组；同一页面的多个 chunk 不重复计为独立来源。不同域名本身不证明独立性。原站文档明确腾讯云已预置版本并提供 SQL；对本云产品部署能力是一手，不能据此主张所有版本通用。

Evidence: ev_00b4876769cb1a7f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/9/content`)

Human decision: PENDING

### CORE-051 — EIV2_ED_002 / freshness

Ledger: EIV2_ED_002-freshness-001

Required Unit: not applicable

Report passage: no emitted claim; see ledger material

AI recommendation: verified

Reason: 文档明确最后更新时间且早于 cutoff，处于 730 天窗口。

Evidence: ev_00b4876769cb1a7f — https://intl.cloud.tencent.com/zh/document/product/409/80360 (`docs\v2\calibration\v2.2.0\enterprise_decision_recommendation\EIV2_ED_002\selected.json#/evidences/9/content`)

Human decision: PENDING

## Human adjudication queue

### ADJ-SEM-001 — EIV2_ED_002 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_ED_002-C019, EIV2_ED_002-C020, EIV2_ED_002-C021, EIV2_ED_002-citation_support-049, EIV2_ED_002-high_risk-001, EIV2_ED_002-high_risk-002

Report/source material: Milvus 需要 Docker Compose 或 Kubernetes 部署;单机版也需要同时运行 etcd、MinIO 和 Milvus 三个容器;生产集群还需配置 Pulsar 或 Kafka。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-002 — EIV2_ED_002 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_ED_002-C015, EIV2_ED_002-C016, EIV2_ED_002-C017, EIV2_ED_002-C018, EIV2_ED_002-citation_support-041, EIV2_ED_002-citation_support-046

Report/source material: pgvector 可直接集成到现有 PostgreSQL 数据库,无需单独基础设施或迁移数据,也无需更改应用架构。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-003 — EIV2_ED_002 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_ED_002-C009, EIV2_ED_002-C010, EIV2_ED_002-C011, EIV2_ED_002-C012, EIV2_ED_002-C013, EIV2_ED_002-C014, EIV2_ED_002-citation_support-022, EIV2_ED_002-citation_support-025, EIV2_ED_002-citation_support-029, EIV2_ED_002-citation_support-031, EIV2_ED_002-citation_support-032, EIV2_ED_002-citation_support-034, EIV2_ED_002-citation_support-035, EIV2_ED_002-citation_support-037, EIV2_ED_002-citation_support-038

Report/source material: pgvector 提供 HNSW 和 IVFFlat 索引,支持 L2 欧氏距离、余弦相似度、内积、L1 曼哈顿距离等距离度量。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-004 — EIV2_ED_002 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_ED_002-C006, EIV2_ED_002-C007, EIV2_ED_002-C008, EIV2_ED_002-citation_support-014

Report/source material: pgvector 支持精确和近似最近邻搜索,并支持 vector、halfvec、sparsevec 等向量类型。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-005 — EIV2_ED_002 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_ED_002-C002, EIV2_ED_002-C003, EIV2_ED_002-C004, EIV2_ED_002-citation_support-002, EIV2_ED_002-citation_support-008, EIV2_ED_002-citation_support-009

Report/source material: pgvector 是 PostgreSQL 的开源扩展,用于在关系型数据库中存储、索引和检索向量。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-006 — EIV2_ED_002 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_ED_002-C024, EIV2_ED_002-C025

Report/source material: pgvector 的备份可使用 pg\_dump,高可用可使用 repmgr 或 Patroni,全部复用 PostgreSQL 生态,不需要学习新工具。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-007 — EIV2_ED_002 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_ED_002-C026

Report/source material: 从架构选型看,向量检索不再是单一选型决策,而需根据向量规模、查询模式、架构偏好选择不同方案。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-008 — EIV2_FV_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_FV_001-C003, EIV2_FV_001-C004, EIV2_FV_001-citation_support-005, EIV2_FV_001-citation_support-006, EIV2_FV_001-citation_support-009, EIV2_FV_001-citation_support-010, EIV2_FV_001-high_risk-001, EIV2_FV_001-high_risk-002

Report/source material: 社区帖子引用 OpenAI 数据保护附录称,OpenAI 可继续处理源自客户数据的去标识化、匿名化或聚合信息,以改进 OpenAI 的系统和服务;该条款与 API 默认不用于训练或改进的表述之间存在边界争议。

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-009 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C018, EIV2_TC_001-C019, EIV2_TC_001-C020, EIV2_TC_001-C021, EIV2_TC_001-high_risk-007, EIV2_TC_001-high_risk-008, EIV2_TC_001-high_risk-009

Report/source material: Filtered vector query performance is a practical edge for pgvector; one source recommends pgvector when filter selectivity is moderate and warns that filtered query performance, index build cost, and missing hybrid primitives are limits\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-010 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C005, EIV2_TC_001-citation_support-011, EIV2_TC_001-citation_support-012, EIV2_TC_001-citation_support-013, EIV2_TC_001-citation_support-014, EIV2_TC_001-citation_support-015, EIV2_TC_001-citation_support-016, EIV2_TC_001-high_risk-002

Report/source material: Hybrid retrieval can be assembled using PostgreSQL full\-text search, pg\_trgm, and reciprocal rank fusion, but one source characterizes pgvector as lacking built\-in hybrid and reranking primitives, recommending pairing with full\-text search instead\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-011 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C003, EIV2_TC_001-citation_support-008, EIV2_TC_001-citation_support-009, EIV2_TC_001-high_risk-001

Report/source material: Hybrid search in pgvector contexts combines vector\-based similarity search with traditional keyword or metadata filtering because vector search handles semantic meaning but can fail on specific keywords or structured constraints\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-012 — EIV2_TC_001 / semantic_claim_bundle

Flags: CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-citation_support-024, EIV2_TC_001-citation_support-026, EIV2_TC_001-citation_support-028, EIV2_TC_001-citation_support-030, EIV2_TC_001-citation_support-032, EIV2_TC_001-high_risk-005, EIV2_TC_001-high_risk-006

Report/source material: Managing pgvector in production requires PostgreSQL expertise: vacuum operations become more complex with large vector tables, index maintenance requires downtime or careful online rebuilding, monitoring vector\-specific performance requires custom instrumentation, and backup and restore times increase significantly with vector data\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-013 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C026, EIV2_TC_001-C027, EIV2_TC_001-C028, EIV2_TC_001-citation_support-051, EIV2_TC_001-citation_support-052, EIV2_TC_001-citation_support-054, EIV2_TC_001-citation_support-055, EIV2_TC_001-citation_support-057, EIV2_TC_001-citation_support-058

Report/source material: Reciprocal rank fusion is mentioned as an available component for hybrid search with pgvector, alongside tsvector and pg\_trgm\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-014 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C030, EIV2_TC_001-C031, EIV2_TC_001-C032, EIV2_TC_001-citation_support-060, EIV2_TC_001-citation_support-066

Report/source material: The PostgreSQL query planner can use pgvector indexes for nearest\-neighbor queries, and vector search can be combined with standard SQL filters, joins, and CTEs in the same query\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-015 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C034, EIV2_TC_001-high_risk-010

Report/source material: Vector columns increase backup sizes significantly, so teams may need incremental backup strategies, separate tablespaces for vector data, and restore\-time testing with realistic data volumes\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-016 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C022, EIV2_TC_001-C023, EIV2_TC_001-C024, EIV2_TC_001-citation_support-038, EIV2_TC_001-citation_support-040, EIV2_TC_001-citation_support-042, EIV2_TC_001-citation_support-043, EIV2_TC_001-citation_support-044, EIV2_TC_001-citation_support-045, EIV2_TC_001-citation_support-046, EIV2_TC_001-citation_support-049

Report/source material: pgvector hybrid search is described as useful for enterprise search, document retrieval in knowledge bases, and RAG because it can filter by structured attributes such as department, author, date, or document type while using vector embeddings for semantic ranking\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-017 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C006, EIV2_TC_001-C007, EIV2_TC_001-C008, EIV2_TC_001-C009, EIV2_TC_001-C010, EIV2_TC_001-C011, EIV2_TC_001-high_risk-003, EIV2_TC_001-high_risk-004

Report/source material: pgvector is the right choice when the dataset fits comfortably on one PostgreSQL instance, filter selectivity is moderate, and transactional consistency with relational data is valued; the edges to watch include index build cost, filtered query performance, missing hybrid and reranking primitives, and absence of horizontal scaling\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-018 — EIV2_TC_001 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TC_001-C035, EIV2_TC_001-C038, EIV2_TC_001-high_risk-011, EIV2_TC_001-high_risk-012

Report/source material: pgvector search quality depends entirely on the upstream embedding model; the extension stores and retrieves vectors but does not understand or improve semantic quality, so poor embeddings produce poor results regardless of database performance\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-019 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C024, EIV2_TM_003-C025, EIV2_TM_003-high_risk-001

Report/source material: AI data residency compliance means LLM inference runs in a specified location such as Frankfurt, while data sovereignty means data in that location stays outside the reach of US law enforcement\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-020 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C013, EIV2_TM_003-C014, EIV2_TM_003-citation_support-013, EIV2_TM_003-citation_support-014

Report/source material: AI services including Amazon Bedrock, Azure OpenAI, and Google Vertex AI are said to accelerate AI usage while also increasing the risk of regulated data leakage into models\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-021 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C004, EIV2_TM_003-C005, EIV2_TM_003-C006, EIV2_TM_003-C007, EIV2_TM_003-citation_support-004, EIV2_TM_003-citation_support-005, EIV2_TM_003-citation_support-006, EIV2_TM_003-citation_support-007

Report/source material: AWS Control Tower is described as a native AWS service for governing secure multi\-account environments with automated account provisioning, policy enforcement, and compliance management\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-022 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C019, EIV2_TM_003-C020, EIV2_TM_003-C021, EIV2_TM_003-C022, EIV2_TM_003-C023, EIV2_TM_003-citation_support-019, EIV2_TM_003-citation_support-020, EIV2_TM_003-citation_support-021, EIV2_TM_003-citation_support-022, EIV2_TM_003-citation_support-023

Report/source material: AWS Prescriptive Guidance recommends a governance framework including compliance monitoring, standardized regulatory documentation, metadata tagging for training data, controls for cross\-border data and service utilization, and regular third\-party audits\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-023 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C039, EIV2_TM_003-C040, EIV2_TM_003-C041, EIV2_TM_003-C042, EIV2_TM_003-C043, EIV2_TM_003-citation_support-039, EIV2_TM_003-citation_support-040, EIV2_TM_003-citation_support-041, EIV2_TM_003-citation_support-042, EIV2_TM_003-citation_support-043, EIV2_TM_003-high_risk-006, EIV2_TM_003-high_risk-007, EIV2_TM_003-high_risk-008, EIV2_TM_003-high_risk-009, EIV2_TM_003-high_risk-010

Report/source material: Amazon Bedrock is described as allowing Claude, Llama, Mistral, and Nova to be run behind a single API endpoint\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-024 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C034, EIV2_TM_003-C035, EIV2_TM_003-C036, EIV2_TM_003-C037, EIV2_TM_003-C038, EIV2_TM_003-citation_support-034, EIV2_TM_003-citation_support-035, EIV2_TM_003-citation_support-036, EIV2_TM_003-citation_support-037, EIV2_TM_003-citation_support-038, EIV2_TM_003-high_risk-005

Report/source material: Amazon Bedrock, Azure AI Foundry, and Google Vertex AI have matured from model hosting services into full\-stack AI development platforms with agent orchestration, retrieval\-augmented generation pipelines, fine\-tuning workflows, and enterprise compliance controls\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-025 — EIV2_TM_003 / semantic_claim_bundle

Flags: HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-high_risk-004

Report/source material: Asia\-Pacific is also seeing strong growth in sovereign cloud initiatives driven by data residency and cybersecurity requirements\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-026 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C015, EIV2_TM_003-citation_support-015

Report/source material: Data residency and sovereignty rules, including GDPR, India DPDP, and emerging sovereignty rules, are described as requiring regional control across hyperscaler regions and availability zones\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-027 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C026, EIV2_TM_003-high_risk-002

Report/source material: For enterprises using US\-headquartered cloud providers, data residency compliance and data sovereignty can be in direct legal conflict\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-028 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C032, EIV2_TM_003-C033, EIV2_TM_003-citation_support-032, EIV2_TM_003-citation_support-033

Report/source material: Gartner's Sid Nag emphasized that generative AI is pivotal in driving cloud market expansion, with new opportunities related to sovereignty, ethics, privacy, and sustainability\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-029 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C044, EIV2_TM_003-C045, EIV2_TM_003-citation_support-044, EIV2_TM_003-citation_support-045

Report/source material: Google Vertex AI is described as suitable for data\-intensive, analytics\-driven enterprises because native integrations into BigQuery, Dataflow, and Looker allow AI training, deployment, and querying without transferring data across systems\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-030 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C008, EIV2_TM_003-C009, EIV2_TM_003-C010, EIV2_TM_003-C011, EIV2_TM_003-C012, EIV2_TM_003-citation_support-008, EIV2_TM_003-citation_support-009, EIV2_TM_003-citation_support-010, EIV2_TM_003-citation_support-011, EIV2_TM_003-citation_support-012

Report/source material: Governance tools are described as offering integrated data governance, AI\-powered automation, metadata and catalog management, hybrid cloud compatibility, and built\-in compliance templates for frameworks such as GDPR and HIPAA\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-031 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C016, EIV2_TM_003-C017, EIV2_TM_003-C018, EIV2_TM_003-citation_support-016, EIV2_TM_003-citation_support-017, EIV2_TM_003-citation_support-018

Report/source material: Governance tools can govern Amazon Bedrock, Azure OpenAI, and Vertex AI usage, redact regulated fields before they reach a foundation model, and provide per\-prompt audit logs for EU AI Act and internal review\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-032 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, CITATION_SUPPORT_UNCERTAIN, HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C046, EIV2_TM_003-C047, EIV2_TM_003-citation_support-046, EIV2_TM_003-citation_support-047, EIV2_TM_003-high_risk-011, EIV2_TM_003-high_risk-012

Report/source material: Model Garden provides access to third\-party models including Anthropic's Claude via a partnership, and Google's Agent Builder powered by the Vertex AI Agent Development Kit handles agentic workflows\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-033 — EIV2_TM_003 / semantic_claim_bundle

Flags: HIGH_RISK_REVIEW, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-high_risk-003

Report/source material: Stricter energy regulations and grid constraints in Europe are described as pushing hyperscalers toward consolidation and high\-efficiency deployments\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-SEM-034 — EIV2_TM_003 / semantic_claim_bundle

Flags: AMBIGUOUS_SEGMENTATION, SEMANTIC_BOUNDARY_REVIEW

Ledger: EIV2_TM_003-C001, EIV2_TM_003-C002, EIV2_TM_003-C003

Report/source material: US regulators including the SEC and FTC are focusing on regulatory compliance for generative AI, particularly algorithmic bias and financial data transparency\.

Reason: One report boundary jointly determines atomic segmentation, citation entailment, and any applicable high-risk obligation. Review once without dropping any pair.

Human decision: PENDING

### ADJ-IND-035 — EIV2_CR_003 / independence

Flags: PUBLISHER_RELATIONSHIP_DISPUTABLE

Ledger: EIV2_CR_003-independence-003

Report/source material: AXCXEPT 在 DeepScaleR-1.5B-Preview 的 HF discussion

Reason: Named author and project identities exist, but same-group versus independent experimental production requires semantic judgment.

Human decision: PENDING

### ADJ-FRESH-036 — EIV2_ED_002 / freshness

Flags: DATE_ROLE_OR_ATTRIBUTION_DISPUTABLE

Ledger: EIV2_ED_002-freshness-003

Report/source material: CSDN afjkdajs 技术趋势文章

Reason: Saved material contains a date clue, but publication/event/reply/sidebar attribution or cutoff relevance requires human judgment.

Human decision: PENDING
