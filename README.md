# Enterprise Insight Agent

**Evidence-Centric Enterprise Deep Research Agent** — built on [GPT Researcher](https://github.com/assafelovic/gpt-researcher).

> Evidence Reliability controls assertion strength, not information presence.

## Overview

Enterprise research needs more than a plausible report with links. An analyst must see which sources support a finding, where evidence conflicts or falls short, and whether a recommendation depends on an unverified premise. Enterprise Insight Agent extends GPT Researcher's research and writing flow with source-aware retrieval, claim-level evidence checks, and inspectable evaluation artifacts. It is a local reference implementation for competitive intelligence and related enterprise research tasks.

## Why Enterprise Insight Agent

GPT Researcher already plans research, searches and scrapes sources, compresses context, and writes reports. This project adds an evidence layer around that flow:

| Engineering change | Purpose |
|---|---|
| Source-aware Evidence / RAG | Keep semantic relevance dominant while using source reliability as a ranking prior; preserve provenance and conflicting evidence. |
| Claim Qualification, Claim Gate, Grounding | Bind draft assertions to evidence, check source qualifications and risk-specific support, then validate the citations actually used. |
| Answer-Critical Claim Review | Focus the audit on findings, comparisons, numerical justifications, conclusions, and recommendation premises that shape the user's answer. |
| Evidence-aware Recommendation | Allow conditional analysis tied to surviving, cited premises; disclose weak evidence instead of presenting it as a verified fact. |
| Trace, Evaluation, Observability | Record ranking components, gate decisions, grounding and repair outcomes, report hashes, costs where available, and bounded stage traces. |

## Architecture

```text
User question → GPT Researcher planning, search, scraping, context compression
              → semantic eligibility + task-aware source reranking → EvidenceContext
              → GPT Researcher Writer draft
              → answer-critical review + draft-claim extraction
              → Claim/Evidence binding + source qualification
              → Claim Gate → citation grounding → bounded repair
              → final report + evidence, trace, and evaluation artifacts
```

The Writer drafts from the complete research context first. The audit examines assertions in that draft; audit-generated assertions absent from it are discarded. `Evidence`, source-level `EvidenceAssessment`, cross-source `EvidenceConsistencyAssessment`, and `ClaimEvidenceLink` remain separate records. The source `authority_score` is a reliability **prior**, never a probability that a claim is true. Task classification selects an interpretable authority weight after semantic eligibility; other `EvidencePolicy` fields are recorded as guidance and are not all enforced as retrieval filters. [Architecture and information flow](docs/v2/INFORMATION_FLOW_SIMPLIFICATION.md) · [Frozen V2 policy](docs/v2/V2_ARCHITECTURE_SPEC.md)

## Core Capabilities

- **Non-destructive evidence handling:** uncertain or conflicting source material remains available for attributed, limited disclosure when validated; it is not silently promoted to a verified assertion or erased from the audit record.
- **Risk-aware factual output:** the Claim Gate can emit, hedge, omit, or leave a claim unresolved. Grounding checks the final citation subset and permits at most one bounded local repair pass. Unresolved claims do not trigger automatic extra retrieval.
- **Decision-focused review:** answer-critical locations and recommendation premises receive explicit review and coverage diagnostics. This review identifies where support must be checked; it does not itself certify truth.
- **Inspectable execution:** the Enterprise API returns persisted reports and evidence diagnostics; each V2 run can retain its Writer draft, structured execution record, report hash, and trace. The existing GPT Researcher routes remain available.

## Evaluation

The [frozen Enterprise Research Benchmark V2](docs/v2/V2_BENCHMARK_SPEC.md) defines **30 cases** across six task categories: **18 development** and **12 reserved holdout** cases, with a 2026-09-05 information cutoff. Its planned quality review covers citation correctness and completeness, strong evidence coverage, reliability of sources actually supporting claims, and high-risk claim corroboration. These require item-level reviewed annotations; runtime counters are diagnostics, not accuracy scores.

After the implementation freeze, the 12 unseen holdout cases were run once through the V2 Enterprise API: **12/12 completed, 0 case-level runtime failures, 0 quality reruns**. A subsequent human Product Generalization Review of the saved artifacts found **basic product generalization**, with an overall **MIXED** result. Engineering stability passed; evidence-aware behavior was mixed and readability acceptable. This does not mean every report passed a product-quality bar. The run was V2-only, so it establishes no quantitative improvement over Original GPT Researcher or V1. See the [final holdout evaluation and category review](docs/v2/V2_HOLDOUT_ONE_PASS_EVALUATION.md).

## Known Limitations

- High-quality first-party sources, independent corroboration, publication dates, and comparable competitor evidence are often unavailable. A source prior cannot fill those gaps.
- Complex comparisons, market trends, and decision recommendations can still rest on weak or incompatible evidence. The final holdout review found conclusions and recommendation premises that need source-level human review before enterprise use.
- The information cutoff is not reliably enforced for all generated content: post-cutoff source metadata appeared in holdout reports. Long reports also repeat qualification language and can be hard to scan.
- The frozen quantitative acceptance criteria remain unevaluated without a complete formal metric ledger and paired comparison. Local SQLite task history and synchronous execution are not a production access-control or distributed job system.

## Quick Start

On Windows with Python 3.11, from the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r multi_agents/requirements.txt
.venv/Scripts/python -m gpt_researcher.enterprise.demo --output outputs/enterprise-demo.json
```

The last command is a credential-free **synthetic** workflow demonstration, not a V2 research run or benchmark. For real research, configure working LLM, embedding, and search providers in a local uncommitted `.env` (for the default providers, `OPENAI_API_KEY` and `TAVILY_API_KEY`), then start the API:

```powershell
.venv/Scripts/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal, submit a V2 request (provider calls may incur cost):

```powershell
$body = @{
    target = 'Microsoft'
    topic = 'Verify the business purpose of Azure OpenAI Service'
    cutoff_date = '2026-09-05'
    dimensions = @('Supported findings', 'Evidence limitations')
    enable_v2_execution = $true
} | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/enterprise/tasks -ContentType 'application/json' -Body $body
```

The POST is synchronous. Open `http://127.0.0.1:8000/docs` for the API, or follow the [local deployment guide](docs/deployment.md) and [request walkthrough](docs/demo.md). See [LICENSE](LICENSE) for license terms.
