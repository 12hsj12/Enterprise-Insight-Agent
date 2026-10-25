# v1 measured runs

These are curated manifests and results from real provider/search executions at
`9004478dc52b4ccdca4cc9bb03c6d86c3e6d1624`, using the existing 8 development / 4 holdout
cases and cutoff **2026-09-05**. The compared variants differ in source reliability
weight (0 versus 0.2). No weight tuning was performed on holdout data.

`development/comparison.json` and `holdout/comparison.json` contain the measured comparisons.
Case records preserve report SHA-256, latency, estimated cost, source count, scoped
search-call count and failures. Four quality metrics are unavailable pending reviewed
claim/citation annotations; null is not zero. No quality or performance gain is claimed.

Full generated reports, context, retrieved sources, evidence and traces remain in the
local ignored directories `outputs/day13-baseline-dev` and
`outputs/day13-source-aware-dev`, plus `outputs/day13-baseline-holdout` and
`outputs/day13-source-aware-holdout`. They are intentionally not published wholesale because
source content can include copyrighted text or sensitive retrieved material. The curated
metrics are not sufficient to independently judge citation correctness without those
raw artifacts. To regenerate fresh raw artifacts, use the commands in `benchmarks/README.md`;
web search and model responses are not deterministic.

The development variants overlapped in wall-clock time, and some runs overlapped Docker
building/offline tests. Treat latency as observed local run time, not a controlled
performance experiment. Costs are the existing provider cost estimator's output, not
billing reconciliation. The historical EI_001 baseline from September 5 is a separate
experiment and is not directly comparable to these same-version ablations.

Both variants completed all 8 development and all 4 reserved holdout cases: 24 live
attempts, zero task failures. Holdout was executed once per variant without tuning.
For the full measured table, test results and interpretation, see
[`docs/v1_validation.md`](../../../docs/v1_validation.md).
