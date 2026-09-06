# Enterprise Insight Agent — Repository Instructions for Codex

## 1. Project mission
This repository is a secondary engineering development of GPT Researcher into **Enterprise Insight Agent**:
an evidence-centric deep-research agent for enterprise competitive intelligence.

Primary technical pillars:
1. Evidence Reliability Engine
2. Source-aware RAG & Context Engineering
3. Evaluation + Observability

Competitive Intelligence is the main business workflow, not a separate infrastructure pillar.

The target is a polished, explainable, portfolio-quality engineering project suitable for AI application / Agent / RAG roles. Reuse the existing GPT Researcher architecture; do not rewrite working components merely for novelty.

## 2. Environment and scope
- Primary local environment: Windows + PowerShell + VS Code
- Python: 3.11.x
- Virtual environment: `.venv`
- Repository remote `origin`: `12hsj12/Enterprise-Insight-Agent`
- Official GPT Researcher should remain conceptually `upstream`
- Continue development on `feat/evidence-engine` unless the user explicitly changes the branch strategy.
- Do not modify unrelated repositories or directories.
- Prefer lightweight local components. Do not introduce Redis, Celery, Kafka, Milvus, Kubernetes, LangGraph, or other heavy infrastructure unless there is a concrete, demonstrated need.

## 3. Git discipline — mandatory
Before changing code:
1. Inspect `git status --short`, current branch, and recent commits.
2. Preserve any pre-existing user changes. Never overwrite or discard them.
3. Confirm work is on `feat/evidence-engine`.

For each meaningful Day/checkpoint:
1. Make a focused set of changes.
2. Run targeted tests.
3. Run relevant regression tests.
4. Inspect `git diff` and `git diff --check`.
5. Ensure no secrets, temporary files, benchmark junk, or unrelated changes are staged.
6. Commit with a clear conventional-style message.
7. Push the commit to `origin feat/evidence-engine`.
8. Confirm the working tree is clean before moving to the next checkpoint.

Authorized normal Git operations:
- status, diff, log, branch inspection
- fetch/pull when safe and needed
- add
- commit
- push to `origin feat/evidence-engine`

Do NOT:
- force-push
- use `git reset --hard`
- amend existing commits
- rewrite/rebase published history
- delete branches or tags
- push tags
- merge into `develop` or `main`
- push directly to `develop` or `main`
- discard user work
unless the user explicitly instructs it.

If remote history unexpectedly diverges, diagnose first and choose the least-destructive solution. Never solve divergence by force.

## 4. Existing architecture boundaries — preserve them
The evidence model responsibilities must remain separated:

- `Evidence` = raw/source/provenance data
- `EvidenceAssessment` = individual source-reliability prior
- `EvidenceConsistencyAssessment` = multi-evidence consistency
- `ClaimEvidenceLink` = explicit claim/evidence relationship

Do not put claim confidence, consistency, or fact-verification semantics into `Evidence`.

Important interpretation:
- `authority_score` is a **source-level reliability prior**.
- It is NOT factual correctness.
- It is NOT claim confidence.
- Cross-evidence consistency is NOT a substitute for fact checking.

Reuse `EvidenceReliabilityEvaluator` and the existing source rules. Do not duplicate domain classification logic.

## 5. Current Source-aware RAG contract
The Day 6 design intentionally uses:

`final_score = (1 - w) * similarity_score + w * authority_score`

Rules:
- semantic similarity remains the primary signal
- source authority is a prior, not truth probability
- default `w = 0.0` preserves baseline behavior
- source-aware mode may use candidate re-ranking only after semantic retrieval/filtering unless benchmark evidence justifies a larger architectural change
- never claim that a weight such as `0.2` is optimal without real benchmark evidence

Backward compatibility matters. Existing GPT Researcher behavior should remain available when source-aware features are disabled.

## 6. Engineering implementation rules
- First inspect the real code/data flow before editing.
- Prefer small, local, testable changes.
- Avoid speculative abstractions.
- Avoid duplicate logic.
- Preserve public interfaces where practical.
- Add explicit types and structured models when they clarify contracts.
- Fail loudly on broken internal invariants rather than silently masking pipeline bugs.
- Add error handling at external boundaries: network, provider calls, persistence, API inputs.
- Add retries/timeouts only where they solve a demonstrated external failure mode.
- Keep dependencies minimal.
- If introducing a dependency, explain why the standard library or existing dependencies are insufficient.

For any nontrivial change, be able to explain:
business problem → original deficit → technical design → implementation → tests → measured result → limitation.

## 7. Testing rules
After each checkpoint:
- run focused tests for the changed module
- run relevant Evidence/RAG/API regression tests
- fix regressions before proceeding

Before final completion:
- run the broadest practical test suite
- run formatting/static checks already supported by the repository where feasible
- run `git diff --check`
- verify final `git status --short` is clean

Never delete or weaken a valid test just to make the suite pass.
If an existing unrelated warning is encountered, record it as technical debt rather than expanding scope unless it blocks the goal.

## 8. Benchmark and evaluation integrity
Benchmark results must be real.

Never:
- invent metric values
- estimate a measured result and present it as measured
- cherry-pick only favorable runs
- modify holdout cases to improve reported performance
- claim improvement without a valid baseline comparison

Benchmark cutoff remains **2026-09-05** unless the user explicitly changes it.

Existing benchmark structure:
- 12 cases total
- 8 development cases
- 4 holdout cases

Core quality metrics:
- Evidence Coverage
- Citation Correctness
- Citation Completeness
- Unsupported Claim Rate

Engineering metrics:
- latency
- cost
- source count
- search calls
- failure rate

Use development cases for iteration. Preserve holdout cases for final evaluation as much as practical. Record configuration, commit SHA, date, and raw outputs needed to reproduce reported numbers.

If external API credentials are unavailable, do all deterministic/local work first and clearly report the blocked benchmark portion rather than fabricating data.

## 9. Secrets, external calls, and generated data
- Never print, commit, or expose `.env`, API keys, tokens, cookies, or credentials.
- Never add secrets to tests or docs.
- Do not modify `.env` unless strictly required; prefer documented environment variables/examples.
- Treat benchmark/API calls as potentially paid. Avoid wasteful repeated runs.
- Do not send repository secrets to external services.
- Generated outputs/logs should stay in ignored locations unless a curated reproducible artifact is intentionally committed.

## 10. Documentation quality
Documentation must describe the code that actually exists.

For architecture and benchmark docs:
- distinguish implemented behavior from proposed future work
- distinguish measured results from expectations
- include limitations
- use diagrams/tables when they improve clarity
- keep README suitable for a recruiter or engineer to understand the project quickly

Do not overstate production readiness. Prefer precise phrases such as “portfolio-grade local deployment” or “reference implementation” when appropriate.

## 11. Long-running Goal execution
When working under `/goal`:
- treat the Day 7–14 plan as one coherent delivery objective with ordered checkpoints
- inspect the repository before implementing each checkpoint
- maintain a concise progress log in an ignored local file under `my-docs/`
- continue autonomously through checkpoints when tests and Git checks pass
- do not pause merely to ask whether to continue
- make reasonable engineering decisions consistent with this file and the plan
- pause only if blocked by missing credentials/required external authorization, a destructive-history decision, an irreconcilable specification conflict, or a failure that cannot be safely resolved

At each checkpoint, record:
- what changed
- tests/commands run
- result
- commit SHA
- remaining work

## 12. Final definition of done
Do not declare the Day 7–14 objective complete until:
- all planned checkpoints are implemented or explicitly documented as blocked with a concrete reason
- relevant tests pass
- final benchmark numbers are real and reproducible if benchmark execution is possible
- Docker/local run path is validated where feasible
- README and architecture/docs match the implementation
- final branch is pushed to `origin feat/evidence-engine`
- no secrets/unwanted generated files are committed
- working tree is clean
- final report contains commits, tests, benchmark results, known limitations, and concise resume/interview-ready project summary
