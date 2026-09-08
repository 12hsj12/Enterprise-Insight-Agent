# Enterprise Insight Agent V2 — Repository Instructions for Codex

## 1. Project mission

This repository is a secondary engineering development of GPT Researcher into **Enterprise Insight Agent**:

> An evidence-centric deep-research agent for enterprise competitive intelligence.

Primary engineering pillars:

1. Evidence Reliability Engine
2. Source-aware RAG & Context Engineering
3. Evaluation + Observability

Competitive Intelligence is the primary business workflow built on these foundations, not a separate infrastructure pillar.

The project should remain an explainable, portfolio-quality engineering system suitable for:

- AI Application Engineering
- AI Agent Engineering
- RAG / LLM Application Engineering
- AI Product Engineering

Reuse the existing GPT Researcher architecture wherever reasonable.

Do not rewrite working components merely for novelty.

---

## 2. Frozen V1 baseline

V1 is frozen experimental evidence.

Frozen V1 branch:

`feat/evidence-engine`

Frozen V1 commit:

`0e3c6b8643db499936312f4ff24e6af1641409e4`

Commit message:

`test: finalize v1 evidence benchmark`

V1 history and benchmark artifacts MUST NOT be rewritten.

Do not:

- modify `feat/evidence-engine`
- amend the frozen commit
- rebase or rewrite published V1 history
- change V1 annotations
- modify V1 benchmark results
- rerun V1 live benchmark merely to improve results
- cherry-pick favorable historical runs

V1 exists as the immutable baseline from which V2 is developed.

---

## 3. Current development branch

All V2 development must occur on:

`feat/evidence-v2`

Before modifying code:

1. inspect `git status --short --branch`
2. verify the current branch is `feat/evidence-v2`
3. preserve any pre-existing user changes
4. inspect relevant existing architecture before editing

Push V2 work only to:

`origin/feat/evidence-v2`

Do not push V2 work to:

- `feat/evidence-engine`
- `develop`
- `main`

Do not merge into `develop` or `main` unless the user explicitly requests it.

---

## 4. Git discipline

For each meaningful checkpoint:

1. make a focused set of changes
2. run targeted tests
3. run relevant regression tests
4. inspect `git diff`
5. run `git diff --check`
6. inspect staged files
7. verify no secrets or unintended generated data are staged
8. commit with a clear conventional-style message
9. push to `origin feat/evidence-v2` when the checkpoint requires remote persistence
10. verify repository state before continuing

Allowed normal Git operations include:

- status
- diff
- log
- branch inspection
- fetch
- safe pull where appropriate
- add
- commit
- push to `origin feat/evidence-v2`

Never:

- force push
- use `git reset --hard`
- amend published commits
- rewrite published history
- delete branches or tags
- push tags
- discard user work
- silently resolve unexpected divergence destructively

If Git history unexpectedly diverges, diagnose first and use the least-destructive solution.

---

## 5. Existing evidence architecture boundaries

Preserve these responsibilities:

### Evidence

Raw evidence, source content and provenance.

### EvidenceAssessment

Individual source-level reliability prior.

### EvidenceConsistencyAssessment

Consistency across multiple evidence items.

### ClaimEvidenceLink

Explicit relationship between a factual claim and supporting/conflicting evidence.

Do not collapse these concepts into one generic confidence score.

Important semantic rule:

`authority_score` is a **source-level reliability prior**.

It is NOT:

- truth probability
- factual correctness probability
- claim confidence
- claim consistency

Reuse the existing `EvidenceReliabilityEvaluator` and existing domain/source classification logic rather than duplicating it.

---

## 6. V1 Source-aware RAG contract

Existing V1 reranking uses:

`final_score = (1 - w) * similarity_score + w * authority_score`

Properties:

- semantic relevance remains the primary retrieval signal
- authority is only a source prior
- `w = 0.0` represents semantic-only baseline behavior
- V1 experimentally used `w = 0.2`
- `0.2` must NOT be described as globally optimal

V1 benchmark results were mixed:

- development Citation Correctness improved materially
- holdout Citation Correctness regressed
- Citation Completeness slightly regressed
- original Evidence Coverage saturated
- evidence selection alone did not constrain unsupported factual generation

Do not claim V1 universally improved research quality.

---

## 7. V2 core direction

V2 introduces two complementary mechanisms.

### 7.1 Query-aware Evidence Selection

Classify each research request into a broad enterprise-intelligence task type and derive an interpretable `EvidencePolicy`.

Initial taxonomy:

1. Factual Verification
2. Technical / Capability Analysis
3. Competitive Comparison
4. Trend / Market Intelligence
5. Conflict & Credibility Resolution
6. Enterprise Decision / Recommendation

An EvidencePolicy may include:

- authority weight
- preferred source types
- freshness requirement
- corroboration requirement
- primary-source preference
- independent-source requirement

Policy decisions must be explainable from task information needs.

Do not optimize policy weights by repeatedly sweeping the benchmark holdout set.

Semantic relevance must remain dominant.

### 7.2 Evidence-gated Claim Generation

V2 must address the gap between evidence selection and generated factual claims.

Conceptual flow:

`Query`
→ `ResearchTaskClassifier`
→ `EvidencePolicy`
→ retrieval
→ reranking
→ evidence context
→ claim planning
→ claim/evidence binding
→ claim gate
→ report generation
→ grounding validation

A factual assertion should not be emitted normally unless sufficient supporting evidence exists.

If evidence is insufficient, appropriate behavior may include:

- omit the claim
- hedge it
- state the evidence limitation
- obtain additional legitimate evidence when supported by the workflow

Never invent evidence.

Never fabricate confidence.

---

## 8. High-risk factual claims

V2 should explicitly model factual claims that require stronger grounding.

Examples include:

- numerical claims
- dates
- release/status/availability claims
- comparative claims
- superlatives
- market metrics
- benchmark claims
- claims involving conflicting evidence

High-risk claims may require:

- one appropriate primary source

or

- multiple independent supporting sources

according to the frozen task policy.

The exact rule must be defined before final benchmark execution.

---

## 9. Engineering design principles

Prefer:

- typed Python
- dataclasses or Pydantic models where useful
- clear contracts
- deterministic policy logic
- pure/testable functions
- explicit configuration
- observable structured diagnostics
- minimal dependencies
- backward-compatible behavior where practical

Avoid:

- speculative abstractions
- duplicate source classification logic
- unnecessary architectural rewrites
- hidden global state
- magic thresholds without explanation
- untyped dictionary-heavy interfaces where a model belongs

Do not introduce heavy infrastructure solely for portfolio decoration.

In particular, do not introduce without a demonstrated need:

- Redis
- Celery
- Kafka
- Milvus
- Kubernetes
- unnecessary LangGraph migration

Environment:

- Windows
- PowerShell
- VS Code
- Python 3.11.x
- `.venv`
- no required NVIDIA/CUDA dependency

Cloud LLM APIs are acceptable.

---

## 10. Explainability requirement

For every nontrivial engineering change, be able to explain:

business problem
→ original system deficit
→ technical mechanism
→ implementation
→ tests
→ measured benchmark result
→ engineering tradeoff
→ limitation

Do not expose private chain-of-thought.

Expose structured decision metadata and concise reasons instead.

Useful V2 diagnostics may include:

- task classification
- classification confidence
- selected EvidencePolicy
- authority weight
- freshness policy
- corroboration policy
- evidence ranking components
- evidence rejection reason
- claim gate decision
- grounding validation result
- high-risk claim status

---

## 11. Benchmark V2

V2 benchmark must be versioned separately from V1.

Target design:

- 30 cases total
- 6 task categories
- 5 cases per category
- 3 dev cases per category
- 2 holdout cases per category

Totals:

- 18 dev
- 12 holdout

The split must be stratified by task category.

Before experimental comparison, freeze:

1. taxonomy
2. case list
3. category labels
4. dev/holdout split
5. information cutoff
6. Required Units
7. high-risk claim rules
8. metric definitions
9. EvidencePolicy definitions
10. acceptance criteria
11. annotation protocol

Do not repeatedly tune against holdout.

Changes after freeze must be explicitly versioned and documented.

---

## 12. Paired retrieval experiment

Where technically meaningful, V2 should reduce live-search confounding by using a shared candidate evidence pool.

Preferred experimental structure:

`one candidate retrieval pool per case`

then compare:

- Baseline
- V1
- V2

over the same candidate evidence where appropriate.

This is intended to reduce retrieval variance.

It does NOT eliminate all nondeterminism.

End-to-end generation can still differ.

Distinguish retrieval-stage evaluation from end-to-end report evaluation when necessary.

---

## 13. Experimental variants

### Baseline

- semantic-only evidence selection
- authority weight `0`
- no task-aware policy
- no claim gate

### V1

- fixed source-aware reranking
- authority weight `0.2`
- no task-aware policy
- no claim gate

### V2

- query-aware EvidencePolicy
- evidence-gated claim generation
- grounding validation

This is primarily a same-codebase ablation.

Do not call Baseline a newly rerun upstream GPT Researcher baseline unless such an experiment is actually performed.

---

## 14. V2 quality metrics

Metrics must be frozen before the final comparison.

Core quality dimensions should include:

### Citation Correctness

Supporting citations / evaluated citations.

### Citation Completeness

Factual claims with valid evidence / factual claims.

`Unsupported Claim Rate = 1 - Citation Completeness`

Therefore Unsupported Claim Rate is only a derived diagnostic, NOT an independent headline metric.

### Strong Evidence Coverage

Measures whether frozen Required Units receive evidence meeting an appropriate evidence-strength rule.

This replaces or supplements the saturated V1 Evidence Coverage.

### Source Reliability Score

Evaluate the reliability of evidence actually supporting claims.

Do not average every retrieved URL indiscriminately.

### High-Risk Claim Corroboration Rate

Measures whether high-risk factual claims satisfy the frozen corroboration requirement.

### Task Classification Accuracy

Predicted category against the frozen benchmark category.

### Category Robustness

Report quality separately for all six categories.

### Generalization Gap

Evaluate stability from dev to holdout.

Engineering metrics should continue to include where available:

- latency
- provider cost
- source count
- search calls
- failure rate
- token usage

Quality and engineering efficiency must be reported separately.

V2 is not required to beat V1 on every latency/cost metric.

---

## 15. Benchmark integrity

Benchmark results must be real.

Never:

- invent metrics
- report estimates as measurements
- alter holdout cases after seeing results
- remove unfavorable cases
- redefine metrics after seeing results
- change annotations to favor V2
- rerun repeatedly until a favorable random outcome appears
- cherry-pick runs
- claim improvement without valid comparison

The benchmark must be capable of concluding that V2 failed.

A failed experiment is an acceptable result.

---

## 16. Annotation integrity

AI-assisted annotation is allowed, but the process must remain auditable.

Before bulk annotation:

1. freeze the rubric
2. establish calibration examples
3. validate factual-claim segmentation
4. validate citation-support matching
5. validate Required Unit scoring
6. validate high-risk claim scoring
7. validate evidence-strength scoring

Preserve:

- report hashes
- raw outputs
- annotation artifacts
- ambiguous-case flags
- reviewer decisions
- scoring inputs

Do not silently use external evidence that is absent from the frozen evaluation protocol.

---

## 17. Testing requirements

After each implementation checkpoint:

- run focused tests for changed modules
- run relevant Evidence/RAG regression tests
- fix genuine regressions before proceeding

Before final completion:

- run all new V2 tests
- run relevant V1 evidence/source-aware tests
- run benchmark tooling tests
- run affected API/persistence tests
- run the broadest practical offline regression suite
- run `git diff --check`
- verify final Git state

Report actual test results.

Do not reuse historical test counts as if newly measured.

Known inherited/unrelated limitations should be reported, not hidden.

Never delete or weaken a valid test merely to make the suite pass.

---

## 18. External calls and cost control

Treat benchmark and provider calls as potentially paid.

Before expensive live execution:

- validate schemas
- validate CLI
- validate output directories
- validate fixtures
- validate dry runs
- validate hashes
- test scoring on synthetic/existing artifacts where possible

Do not use paid live benchmark runs as a debugging mechanism.

Record actual estimated cost.

Do not rerun the frozen V1 live benchmark.

---

## 19. Secrets and generated files

Never expose or commit:

- `.env`
- API keys
- tokens
- cookies
- credentials
- private secrets

Do not modify `.env` unless strictly necessary.

Generated outputs should normally remain ignored unless intentionally promoted as curated reproducible artifacts.

Inspect staged files before every commit.

---

## 20. V2 batch execution workflow

V2 development should use a bounded, operator-mediated batch workflow rather than a
programmatic multi-agent orchestrator.

Preferred execution pattern:

Planner
→ bounded batch specification
→ fresh Codex worker conversation
→ focused tests
→ Git checkpoint
→ independent review for meaningful/core batches
→ repair if necessary
→ next batch

The user acts only as the execution coordinator. The user should not be required to
manually implement code.

Each implementation batch should clearly define:

- batch id
- objective
- rationale
- dependencies
- allowed paths
- forbidden paths
- implementation requirements
- tests
- acceptance criteria
- expected artifacts
- expected Git checkpoint

Use a fresh Codex conversation when starting a substantial new batch so that unrelated
context from previous implementation work does not accumulate.

Programmatic Codex App Server orchestration is explicitly out of scope for the V2 core
deliverable and must not be treated as a prerequisite for implementing the Evidence V2
architecture.

The absence of an automated orchestrator must not block downstream V2 core implementation,
testing, evaluation, or benchmark work.

---

## 21. Review and repair

A worker should not be its sole final reviewer for a meaningful or core implementation batch.

Independent review is required for major V2 checkpoints, including:

- core architecture implementation
- query-aware evidence selection
- claim grounding and claim gate
- benchmark and evaluation infrastructure
- final V2 qualification

For small implementation changes, focused tests and Git inspection may be sufficient.

If a meaningful batch fails independent review:

1. record the concrete review findings
2. use a fresh Codex conversation to repair the same batch
3. rerun the relevant focused and regression tests
4. request independent review again before proceeding

Do not continue downstream work when a genuine core dependency remains broken.

A failed batch is not a failed V2 project. Resolve or explicitly re-scope the affected
implementation before continuing.

Programmatic automatic repair loops and orchestration-specific blocker handling are out of
scope for the V2 core deliverable.

---

## 22. Documentation

Documentation must match the implementation that actually exists.

Clearly distinguish:

- implemented behavior
- proposed future work
- measured results
- hypotheses
- limitations

Do not overstate production readiness.

Do not turn documentation into marketing copy.

Use precise engineering language.

---

## 23. Definition of done for V2

Do NOT declare V2 complete until:

- V2 architecture/specification is frozen
- implementation batches are completed or explicitly blocked
- relevant tests have actual recorded results
- Benchmark V2 is completed if provider access permits
- benchmark metrics are real
- frozen acceptance criteria are evaluated
- favorable and unfavorable results are both reported
- final documentation matches implementation
- all intended artifacts are committed
- `feat/evidence-v2` is pushed to `origin`
- local and remote V2 branch are synchronized
- working tree is clean
- no secrets or unintended generated files are committed
- final V2 delivery documentation accurately records completed work, measured results,
  unresolved limitations, and any explicitly de-scoped items

The final V2 project artifact should be:

- `V2_FINAL_DELIVERY_REPORT.md`

If a core implementation batch cannot be completed, record the limitation accurately in
the relevant development or review documentation rather than creating an
orchestration-specific blocker artifact.

Never fabricate completion.
Never fabricate benchmark improvement.
Never rewrite V1 evidence.

## 24. Codex batch autonomy

Within an explicitly authorized V2 implementation batch, Codex should autonomously
complete the engineering loop:

inspect repository
→ implement
→ add/update tests
→ run focused tests
→ run relevant regressions
→ inspect diff
→ run git diff --check
→ commit
→ push to feat/evidence-v2
→ report results

Do not stop to ask the user to manually run routine Git, test, formatting, or inspection
commands when Codex can safely perform them itself.

Stop and request user intervention only when encountering a genuine decision boundary,
including:

- unexpected dirty or conflicting user changes
- branch/history inconsistency
- secrets or credential risk
- ambiguous frozen V2 requirements
- need to modify frozen benchmark/specification artifacts
- destructive Git operations
- benchmark/provider spending not already authorized

Implementation details may be decided autonomously within the frozen V2 architecture.
Research design, benchmark definitions, taxonomy, Required Units, metrics, acceptance
criteria, and frozen V1 artifacts must not be changed without explicit authorization.
