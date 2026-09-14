# V2 Utility Correction Batch 2 Delivery

## Decision

PASS

The batch recovers source identity and publication metadata already present in retrieved
URLs, search-result fields, page metadata, or explicit article headers. It does not add
retrieval, provider, or LLM calls.

## Metadata Path

- Current inputs: retriever result fields, scraper URL/title/content, HTML meta tags, and
  JSON-LD.
- Extraction: `gpt_researcher/evidence/metadata.py` applies deterministic field-level
  precedence and conservative date parsing.
- Preservation: search metadata is retained across the scrape boundary; source metadata is
  copied into LangChain `Document` metadata and then typed `Evidence` records.
- Qualification integration: the existing source-identity resolver continues to consume
  `source_owner`, `source_organization`, then `publisher`. Verified publication dates now
  populate the existing grounding audit input. No qualification rule changed.

## Source Identity

- Existing `publisher`, `source_organization`, and `author` fields are reused.
- `SourceRole` is limited to `FIRST_PARTY`, `GOVERNMENT_OR_STANDARD_BODY`, `THIRD_PARTY`,
  and `UNKNOWN`.
- The exact-host table is intentionally small: OpenAI developer/first-party hosts, AWS and
  AWS Docs, Google Cloud, Microsoft Learn, and NIST.
- Canonical aliases are limited to explicit names for those mapped hosts.
- GitHub has no host-level mapping and remains unknown without an existing reliable
  repository-owner association.
- A source role is descriptive metadata. It does not set `is_primary_source`.

## Publication Dates

Resolution precedence is:

1. explicit structured `datePublished` / `article:published_time`;
2. explicit visible `Published` / `Publication date` / `发布日期` near the article header;
3. an explicit search-result publication-date field;
4. unknown.

`dateModified`/`article:modified_time` and visible update labels populate `updated_date`
separately. They never replace `publication_date`. Conflicting values set
`metadata_conflict=true`, while the highest-precedence value is retained. No URL-pattern
date inference is implemented. Unlabeled dates, footer years, event dates, comments,
and late related/recommendation-card dates are rejected.

## Calibration Replay

The replay read the six frozen V2.2 development `selected.json` artifacts only. Every
selected chunk was processed exactly as stored, without reordering or page-offset
extrapolation; no metadata value, case label, or expected answer was inserted. The date
result is therefore a conservative lower bound because the saved artifacts omit original
HTML and unselected page regions.

### Before

- known publisher: 0
- unknown publisher: 191
- known publication date: 0
- unknown publication date: 191
- freshness computable: 0
- first-party identifiable: 0

### After

- known publisher: 18
- unknown publisher: 173
- known publication date: 1
- unknown publication date: 190
- freshness computable: 1
- first-party identifiable: 16

The machine-readable result is in `docs/v2/V2_SOURCE_METADATA_CALIBRATION_REPLAY.json`.

## Qualification Impact

- source identity newly usable: 18 evidence records;
- freshness newly computable: 1 evidence record;
- first-party newly identifiable: 16 evidence records;
- the single verified publication date is older than the 180-day diagnostic window. A
  verified date is therefore not treated as automatically fresh.

These are metadata-input improvements, not rerun Gate outcomes or report-quality claims.

## False Positive Check

- source-identity false positives on curated fixtures: 0;
- publication-date false positives on curated fixtures: 0;
- AWS official metadata did not primary-qualify an AWS source for a Microsoft claim;
- a third-party publisher did not become primary through source role or authority;
- a conflicting structured publisher on an official host was flagged and not labeled
  first-party.

## Safety

- primary semantics unchanged;
- independence rule unchanged;
- freshness threshold unchanged;
- Claim Gate implementation and risk mapping unchanged;
- grounding rules unchanged; the existing audit receives recovered publication dates;
- V1 branch, commit, annotations, and benchmark artifacts unchanged;
- no `.env` or credential material read into artifacts or staged.

## Complexity

No source/company graph, general NER, LLM metadata judge, LLM date extractor, new
retrieval, alias database, reputation service, external API, or semantic source resolver
was introduced. The implementation is a pure deterministic helper plus a nine-entry
exact-host map.

## Tests

- final focused metadata/qualification/grounding/trace tests: 65 passed;
- final independent relevant regression: 100 passed;
- broad offline module-isolated regression: 843 collected, 841 passed, 2 skipped,
  0 failed; the runner intentionally excluded its three declared live modules;
- an initial broad run exposed one scraper-stub compatibility regression; metadata parsing
  was made non-blocking and the full suite then passed;
- compile check: passed;
- `git diff --check`: passed.

Warnings were limited to the inherited pytest configuration warning and dependency
deprecations; no test failure was hidden.

## Runtime Calls

- provider: 0
- search: 0
- development benchmark: 0
- holdout benchmark: 0

## Independent Review

The first review found false-positive risks in early related-card visible dates, ambiguous
JSON-LD articles, and replay chunk reordering. All three findings were repaired. A second
review found two narrower deterministic counterexamples (a single explicit non-matching
JSON-LD URL and an unmarked nearby story); both were repaired with fail-closed behavior and
new tests. Final independent re-review: PASS, with 100 relevant tests passed and no remaining
deterministic metadata, semantic, pipeline, runtime-call, or scope-control blocker.

## Git State

Implementation target: `feat/evidence-v2` based on accepted Batch 1 commit
`23606b895355ce8025d7aada7becf3f0970c3f23`. Final commit, push, synchronization, and
clean-tree verification are recorded in the delivery response.

## Remaining Limitations

- Unknown remains the correct result for most third-party pages lacking explicit publisher
  metadata.
- Visible dates require an explicit label associated with the saved page title and are
  bounded to the header region; unusual layouts may remain unresolved.
- Exact-host canonicalization covers only the small mapped set and does not infer corporate
  relationships.
- Saved calibration artifacts contain selected text chunks rather than original HTML, so
  the offline replay cannot measure JSON-LD/OpenGraph recovery that future normal runs will
  preserve.

## Next Step

Proceed to Batch 3: bounded evidence-gap retrieval after independent review.
