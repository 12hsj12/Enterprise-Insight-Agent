# Enterprise Insight Agent

**面向竞争情报及相关决策任务、以证据为依据的企业研究 Agent。** 本产品沿用 [GPT Researcher](https://github.com/assafelovic/gpt-researcher) 的研究与写作基础。

[English](README.md) · [简体中文](README-zh_CN.md)

> 证据可靠性决定论断应当表述得多强，不决定信息是否保留。

## 项目定位

Enterprise Insight Agent 是一个本地参考实现，面向需要核查研究发现依据、来源分歧和建议前提是否存在不确定性的研究任务。产品流程将研究规划、网页检索、证据评估、关键论断审查、引用核验和可追溯报告记录整合在一起。

本项目沿用 GPT Researcher 的研究与写作基础。来源说明和适用许可证见[许可证与来源](#许可证与来源)。

## 技术架构

```text
研究请求
  → 研究规划、搜索、抓取与上下文压缩
  → 语义筛选与任务感知的来源重排
  → 包含来源信息和诊断数据的结构化 EvidenceContext
  → 报告草稿与答案关键论断审查
  → 论断/证据绑定、来源资质检查、Claim Gate 与引用核验
  → 有界局部修复、最终报告、运行追踪与评测记录
```

Writer 先基于研究上下文起草，再由证据审查流程检查草稿中的论断；审查过程中生成但未出现在草稿中的论断会被丢弃。`Evidence`、单来源的 `EvidenceAssessment`、跨来源的 `EvidenceConsistencyAssessment` 和 `ClaimEvidenceLink` 是相互独立的记录。`authority_score` 是来源可靠性先验，不是论断为真的概率。任务分类会在语义筛选后选择来源权重；`EvidencePolicy` 的其他字段属于指导信息，并非都会作为检索过滤条件。详见[架构规范](docs/v2/V2_ARCHITECTURE_SPEC.md)和[信息流说明](docs/v2/INFORMATION_FLOW_SIMPLIFICATION.md)。

## 核心模块

| 模块 | 职责 |
|---|---|
| `gpt_researcher/skills/researcher.py`、`gpt_researcher/context/` | 研究规划、检索、压缩、来源感知上下文与来源追溯。 |
| `gpt_researcher/evidence/` | 证据记录、元数据、可靠性先验、论断绑定、一致性、资质和引用核验。 |
| `gpt_researcher/enterprise/` | 请求工作流、任务策略、答案关键审查、报告诊断、追踪和结构化结果。 |
| `backend/server/enterprise_api.py`、`backend/server/sqlite_report_store.py` | 本地企业任务 API 与 SQLite 任务历史。 |
| `benchmarks/`、`tests/`、`scripts/run_offline_tests.py` | 冻结评测输入与结果、回归覆盖和按模块隔离的离线测试运行器。 |

## 运行方式

项目要求 Python 3.11 或更高版本。依赖文件声明的是最低版本范围，不是完整锁定的环境；Docker 构建也使用相同的 requirements 文件。在 Windows 仓库根目录运行：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r multi_agents/requirements.txt
.venv/Scripts/python -m gpt_researcher.enterprise.demo --output outputs/enterprise-demo.json
```

演示使用合成样例数据，不调用模型或搜索服务，只展示软件流程，不是在线研究运行或基准评测。

进行真实研究前，请在本地且不提交的 `.env` 中配置可用的 LLM、embedding 和搜索服务（默认配置使用 `OPENAI_API_KEY` 和 `TAVILY_API_KEY`），然后启动 API：

```powershell
.venv/Scripts/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

在另一个 PowerShell 终端提交企业研究任务。服务商调用可能产生费用：

当前本地 API 通过请求字段 `enable_v2_execution` 启用证据研究工作流。

```powershell
$body = @{
    target = 'Microsoft'
    topic = '核实 Azure OpenAI Service 的商业用途'
    dimensions = @('有来源支持的发现', '证据局限')
    enable_v2_execution = $true
} | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/enterprise/tasks -ContentType 'application/json' -Body $body
```

请求以同步方式执行。API 文档位于 `http://127.0.0.1:8000/docs`；[部署指南](docs/deployment.md)和[请求演示](docs/demo.md)介绍本地运行与持久化。

## 测试与评测

安装测试依赖：`python -m pip install -e ".[test]"`。随后使用一个新的输出目录运行按模块隔离的离线测试：

```powershell
.venv/Scripts/python scripts/run_offline_tests.py --output outputs/offline-run --workers 4
```

运行器会设置 `GPTR_BLOCK_NETWORK=1`，并排除三个在线/服务商测试模块：`test_researcher_logging.py`、`test_logging_output.py` 和 `test_mcp.py`。每次运行请使用新的输出目录。

[冻结的基准规范](docs/v2/V2_BENCHMARK_SPEC.md)定义了六类共 **30 个案例**：**18 个开发集案例**和**12 个保留集案例**，信息截止日期为 2026-09-05。冻结后，12 个保留集案例通过企业 API 各运行一次：**12/12 完成，案例级运行失败 0，质量重跑 0**。对已保存报告进行的人工产品泛化审查结果为 **MIXED（总体混合）**：工程稳定性通过，证据行为表现不一，可读性可接受。完成数量不代表报告质量分数，也没有配对定量比较证明本产品相对上游项目有提升。详见[基准规范](docs/v2/V2_BENCHMARK_SPEC.md)和[保留集评测](docs/v2/V2_HOLDOUT_ONE_PASS_EVALUATION.md)。

## 已知限制

- 高质量一手来源、独立佐证、发布日期及可比的竞争者证据可能缺失；来源可靠性先验无法弥补这些缺口。
- 复杂比较、趋势分析和决策建议仍可能依赖薄弱或不兼容的证据。保留集审查发现，部分结论和建议前提在企业使用前需要人工核查原始来源。
- 生成内容未能始终遵守 2026-09-05 信息截止日期；保留集报告中出现过截止日期之后的来源元数据。长报告可能重复限定说明，不易快速浏览。
- 缺少完整正式指标台账和配对比较，因此尚未评估冻结的定量验收标准。运行时计数是诊断信息，不是准确率分数。
- 本地 API 使用同步执行和 SQLite 历史记录；目前没有身份验证、多租户隔离、持久化分布式队列或分布式任务协调。

## 许可证与来源

本仓库以 [GPT Researcher](https://github.com/assafelovic/gpt-researcher) 为基础，沿用其研究和写作基础并作为一个产品继续构建。本仓库许可证为 [Apache License 2.0](LICENSE)；请保留适用的上游声明，并查阅上游仓库了解其自身许可条款。Python distribution 为保持兼容继续使用 `gpt-researcher` 包名。

## 文档导航

- [文档首页](docs/docs/welcome.md)
- [架构规范](docs/v2/V2_ARCHITECTURE_SPEC.md) · [冻结的基准规范](docs/v2/V2_BENCHMARK_SPEC.md) · [保留集评测](docs/v2/V2_HOLDOUT_ONE_PASS_EVALUATION.md)
- [基线基准协议](docs/baseline_protocol.md) · [验证记录](docs/v1_validation.md)
- [许可证](LICENSE) · [贡献指南](CONTRIBUTING.md)
