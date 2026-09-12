# Development calibration capture review

This task authorizes observation and persistence for the six selected development
cases, independently of the later paired benchmark. Frozen benchmark and Agent
semantics are unchanged.

The existing workflow already exports report bytes, integrated Claim/Binder/Gate/
Grounding records and traces. `ContextCompressor` now has two opt-in observations:
pages before compression, and eligible chunks after the existing similarity filter
but before source-aware ranking. A context-local collector makes detached JSON
snapshots. It never supplies objects back to retrieval or generation. Existing
selected evidence, assessments and retrieval diagnostics are exported separately.
Missing candidate scores are not estimated. This is not a frozen replay pool or a
verified cutoff eligibility filter.

Page text is limited to 50,000 characters, with original sanitized text length,
truncation flag and full sanitized-text hash. Chunk text is saved separately, so a
human can inspect selected supporting text even when a page is truncated. Only
explicit allowlisted metadata is copied; missing organization or date metadata is
not inferred. Optional non-text metadata is skipped with field-name diagnostics.
Non-finite or malformed observations record a safe error without changing research.
Known configured secrets, authentication values and URL credentials are redacted.
Environment mappings, headers and exception messages are not capture inputs.

The execution adapter posts to the production enterprise FastAPI router using
in-process `httpx.ASGITransport`. It uses the actual `IntelligenceWorkflow` and
`GPTResearcher`, with real LLM/search/scrape/embedding implementations. No research
object is mocked. The six IDs are fixed; output directories are append-only and
each case receives one POST. The query and Required Unit descriptions are carried
by the existing request fields. Gold category labels and strength rules are not
injected into the classifier or Claim authoring. The existing cutoff instruction
remains an instruction, not a date filter.

An independent read-only agent reviewed this bounded change. Two initial findings
were repaired before paid execution: authentication-header redaction and loss of
candidate events on non-text optional metadata. A follow-up warning about redundant
JSON-string scrubbing was checked against the actual file: `write(task.json, task)`
uses recursive value scrubbing and has no JSON-string scrub/parse operation.

New deterministic tests compare capture-on/off outputs through the real compressor,
ranking, `integrate_claims`, Gate, Grounding and report renderer, with identical
retrieval invocation counts. Additional tests cover detached stable snapshots,
candidate/selected distinction, secret redaction, bounded text, optional metadata
and safe malformed/non-finite failures. Six capture tests passed before live use.
The first related regression run passed 82 tests; broader final results are recorded
in the delivery material. Local embedding preflight produced a 384-dimensional
vector without any paid LLM/search call.

Cost fields remain the runtime's estimates. They must not be described as reconciled
provider invoices; inherited generic token/embedding pricing may differ from the
configured DeepSeek and local HuggingFace costs. Unavailable billing and token
information stays unavailable.
