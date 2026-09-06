# Resume and interview package

## Resume bullet candidates

- Extended GPT Researcher into an evidence-centric competitive-intelligence application,
  preserving source provenance through semantic retrieval and exposing typed report/evidence APIs.
- Implemented configurable source-prior reranking after semantic filtering, with a
  backward-compatible zero-weight path and separate evidence, reliability and consistency contracts.
- Built a reproducible 12-case evaluation workflow with an 8/4 development/holdout split,
  versioned manifests, retained failures and report-hash-bound reviewed citation metrics.
- Added bounded async run tracing, SQLite task history and interrupted-run recovery, and
  validated a non-root Docker deployment plus deterministic API-to-persistence integration tests.

Do not add an accuracy or latency improvement percentage: the present runs do not establish
one. Counts and measured results should be quoted from `docs/v1_validation.md`, not memory.

## 30-second pitch

我基于 GPT Researcher 做了一个面向企业竞争情报的二次工程开发。重点不是重新搭建
Agent，而是让研究结果可检查：检索后的证据保留来源，用可配置的来源可靠性先验参与
重排，同时把原始证据、来源评估、跨证据一致性分开。外围补上固定评估集、运行追踪、
类型化 API、SQLite 任务历史和 Docker 本地部署。项目能展示从研究请求到证据、报告、
运行诊断和历史结果的完整链路，但我不会把来源权威性说成事实正确率。

## Explain the project in two minutes

**Business problem.** Enterprise research needs more than a fluent report. Analysts need
to inspect supporting sources, understand selection behavior and find uncertainty before
using a conclusion. Generic research output does not by itself establish those guarantees.

**Original deficit.** The upstream execution pipeline was reusable, while structured
provenance, explicit source-prior behavior, reproducible evaluation and local task recovery
needed additional engineering. Inspection also found evidence-registration code in the
wrong compression method; fixing the actual data flow was more useful than adding a new stack.

**Design.** Keep semantic retrieval first, add a small configurable source prior, and retain
the zero-weight baseline. Keep evidence content separate from source assessment and from
claim relationships. Reuse `conduct_research` and `write_report` for the business workflow.

**Implementation and verification.** Pydantic contracts expose evidence and diagnostics
alongside the report. Context-local bounded traces record selected scores and stage timing.
SQLite transactions persist task records; startup marks interrupted work without replaying
paid calls. Tests exercise fake external boundaries with actual RAG/evidence/workflow/store
code. A fixed dataset and frozen configs produce raw artifacts, hashes and measured metrics.

**Measured result and limitation.** Development runs completed 8/8 cases per variant. This
is execution evidence, not a quality-improvement result. The quality scorer needs reviewed
annotations, live retrieval is nondeterministic, and overlapping local workloads limit
latency interpretation. The deployment is intended for local portfolio demonstration.

## Technical decisions and tradeoffs

| Choice | Reason | Cost or limitation |
|---|---|---|
| Reuse GPT Researcher | Existing search/writing behavior and integrations already work | Inherited dependencies and uneven provenance across retrieval paths |
| Rerank after semantic filtering | A source prior should not bypass relevance | Cannot recover a relevant source absent from the candidate set |
| Default weight zero | Preserve retrieval baseline and compare explicitly | Benefits must be demonstrated; no optimal weight claimed |
| Explicit claim links | Separate source reputation from support for a particular statement | Quality/consistency work still needs reviewed relationships |
| Local bounded traces | Explain execution without an infrastructure backend | No distributed tracing; planning/MCP search counts incomplete |
| SQLite and one worker | Lightweight persistent history with transactional writes | No durable queue, distributed lease or automatic continuation |
| Manual/judged metric inputs | Citation correctness is semantic, not link presence | Requires annotation effort before a quality claim is defensible |

## Likely interview questions

**What did you build beyond the upstream project?**
Evidence/provenance integration, configurable source-aware RAG, the competitive-intelligence
contract and orchestration, evaluation tooling, bounded traces, enterprise routes, SQLite
history/recovery, deployment verification and project documentation. Planning/search/writing
and much of the original application remain upstream functionality.

**Does an official source mean the claim is true?**
No. `authority_score` is only a source prior. Official sources can be biased or outdated.
Claim correctness requires checking the cited passage, its date, and independent evidence.

**Why use weight 0.2?**
It is an engineering candidate, not a learned optimum. I kept weight zero as a same-version
baseline. I would use the development set to test a predeclared weight grid and evaluate
the selected configuration once on holdout after annotations are available.

**Why not add a neural reranker or vector database?**
There was no measured need. Reusing the existing semantic retrieval and source rules kept
the change small and testable. A more expensive component needs a benchmark showing the
deficit it fixes, along with its latency/cost tradeoff.

**What does recovery actually recover?**
Stored request/result metadata and task history. A running task left by a stopped process
is marked interrupted on startup. It does not resume a model call or automatically repeat
research; doing so could duplicate charges and needs durable execution semantics.

**How did you prevent evaluation overclaiming?**
Frozen cases, an explicit holdout split, commit/config/runtime manifests, raw artifacts,
retained failures, null unavailable metrics and report-hash-bound annotations. I distinguish
the historical upstream baseline from the current weight ablation and do not attribute
uncontrolled latency differences to the ranking change.

**What would you improve first?**
Collect reviewed claim/citation annotations, widen structured provenance to MCP/vector-store
paths, implement verifiable date handling, and run controlled candidate-ranking experiments.
For shared deployment I would then add authorization, resource limits and explicit durable
task execution semantics based on an actual workload.
