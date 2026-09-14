"""Offline Batch 2 coverage for conservative source/date enrichment."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from gpt_researcher.context.compression import ContextCompressor
from gpt_researcher.enterprise.integration import ClaimProposal, register_proposal
from gpt_researcher.enterprise.trace import ResearchTraceRecorder
from gpt_researcher.evidence.metadata import (
    enrich_page_metadata,
    extract_structured_html_metadata,
    extract_visible_dates,
    search_result_metadata,
)
from gpt_researcher.evidence.models import Evidence, EvidenceContext, SourceRole
from gpt_researcher.scraper.beautiful_soup.beautiful_soup import BeautifulSoupScraper
from scripts.replay_source_metadata_calibration import replay


def _page(url="https://example.com/article", content="Article body"):
    return {"url": url, "title": "Article", "raw_content": content}


def _proposal(primary_name):
    return ClaimProposal.model_validate({
        "claims": [{
            "text": "A bounded claim.",
            "risk_types": ["numeric_value"],
            "is_material": True,
            "entity_references": [{"reference_id": "entity", "name": primary_name}],
            "relations": [{
                "evidence_id": "ev",
                "relation": "support",
                "supported_entity_reference_ids": ["entity"],
                "primary_source_entity_reference_ids": ["entity"],
            }],
            "cited_evidence_ids": ["ev"],
        }],
        "source_identities": [],
    })


def test_jsonld_and_open_graph_dates_and_publisher_are_extracted():
    jsonld = extract_structured_html_metadata("""
      <html><head><script type="application/ld+json">
      {"@type":"NewsArticle","datePublished":"2026-05-10T08:30:00Z",
       "dateModified":"2026-07-10","publisher":{"@type":"Organization","name":"Acme News"},
       "author":{"@type":"Person","name":"Ada Author"}}
      </script></head><body>Body</body></html>""", page_url="https://example.com/story")
    assert jsonld == {
        "publication_date": "2026-05-10",
        "updated_date": "2026-07-10",
        "publisher": "Acme News",
        "author": "Ada Author",
    }

    og = extract_structured_html_metadata("""
      <meta property="article:published_time" content="2026-04-03T01:00:00+00:00">
      <meta property="article:modified_time" content="2026-04-04">
      <meta property="og:site_name" content="Example Journal">""")
    assert og["publication_date"] == "2026-04-03"
    assert og["updated_date"] == "2026-04-04"
    assert og["site_name"] == "Example Journal"


def test_beautiful_soup_scraper_captures_head_metadata_before_cleaning():
    class Response:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        encoding = "utf-8"
        content = b"""<html><head><title>Story</title>
          <meta property="article:published_time" content="2026-05-10">
          <meta property="og:site_name" content="Example Publisher">
          </head><body><article>Long article body with enough useful content to parse.</article></body></html>"""

    class Session:
        def get(self, url, timeout):
            return Response()

    scraper = BeautifulSoupScraper("https://example.com/story", Session())
    content, _, title = scraper.scrape()
    assert title == "Story"
    assert "Long article body" in content
    assert scraper.metadata == {
        "publication_date": "2026-05-10",
        "site_name": "Example Publisher",
    }


def test_visible_dates_require_explicit_article_labels_and_keep_updated_separate():
    values = extract_visible_dates(
        "Headline\nPublished:\nMay 10, 2026\nUpdated: July 10, 2026\nBody",
        title="Headline",
    )
    assert values == {
        "publication_date": "2026-05-10",
        "updated_date": "2026-07-10",
    }
    assert extract_visible_dates(
        "中文文章标题\n发布日期：2025-04-22 14:23:15", title="中文文章标题"
    ) == {
        "publication_date": "2025-04-22"
    }
    assert extract_visible_dates(
        "Privacy Policy\nUpdated: 2026年2月6日\nBody", title="Privacy Policy"
    ) == {
        "updated_date": "2026-02-06"
    }


def test_sidebar_footer_related_and_event_dates_are_rejected():
    text = """Article body says the event occurred 2026-05-10.
    Related articles
    Recommended story 2026-09-10
    Comments posted 2026-09-11
    Copyright © 2026 Example
    Last accessed 2026-09-12
    """
    assert extract_visible_dates(text, title="Article body") == {}
    late_related = (
        "Main article without a publication date. " + "body " * 1200
        + "\nRelated articles\nPublished: September 10, 2026"
    )
    assert extract_visible_dates(late_related, title="Main article") == {}
    early_related = (
        "Current Article\nRelated Articles\nPublished: September 10, 2026"
    )
    assert extract_visible_dates(early_related, title="Current Article") == {}
    sidebar_first = (
        "Sidebar\nCurrent Article\nPublished: September 10, 2026\n"
        "Current Article\nMain body"
    )
    assert extract_visible_dates(sidebar_first, title="Current Article") == {}


def test_related_article_jsonld_is_not_attributed_to_current_page():
    html = """
      <script type="application/ld+json">[
        {"@type":"NewsArticle","url":"https://example.com/related",
         "datePublished":"2026-09-10","publisher":{"name":"Related News"}},
        {"@type":"NewsArticle","mainEntityOfPage":{"@id":"https://example.com/current"},
         "datePublished":"2026-05-10","publisher":{"name":"Current News"}}
      ]</script>"""
    matched = extract_structured_html_metadata(
        html, page_url="https://example.com/current"
    )
    assert matched["publication_date"] == "2026-05-10"
    assert matched["publisher"] == "Current News"

    ambiguous = extract_structured_html_metadata(html)
    assert "publication_date" not in ambiguous
    assert "publisher" not in ambiguous
    assert ambiguous["metadata_conflict"] is True

    single_mismatch = extract_structured_html_metadata(
        """<script type="application/ld+json">
        {"@type":"NewsArticle","url":"https://example.com/related",
         "datePublished":"2026-09-10","publisher":{"name":"Related News"}}
        </script>""",
        page_url="https://example.com/current",
    )
    assert "publication_date" not in single_mismatch
    assert "publisher" not in single_mismatch
    assert single_mismatch["metadata_conflict"] is True


def test_unmarked_nearby_story_date_is_not_a_visible_article_date():
    text = (
        "Current Article\nThis is the current article summary.\n"
        "Another story\nPublished: September 10, 2026"
    )
    assert extract_visible_dates(text, title="Current Article") == {}


def test_search_result_date_has_explicit_provenance_and_generic_date_is_ignored():
    assert search_result_metadata({
        "published_date": "2026-06-01", "site_name": "Example Media"
    }) == {"publication_date": "2026-06-01", "publisher": "Example Media"}
    assert search_result_metadata({"date": "2026-06-01"}) == {}
    enriched = enrich_page_metadata(
        _page(), provider_metadata={"publication_date": "2026-06-01"}
    )
    assert enriched["publication_date"] == "2026-06-01"
    assert enriched["metadata_provenance"]["publication_date"] == "SEARCH_RESULT_METADATA"


def test_known_official_third_party_government_github_and_unknown_roles():
    aws = enrich_page_metadata(_page("https://docs.aws.amazon.com/service/guide.html"))
    assert aws["publisher"] == "Amazon Web Services"
    assert aws["source_role"] == SourceRole.FIRST_PARTY.value

    third_party = enrich_page_metadata(
        _page(), structured_metadata={"publisher": "Example Media"}
    )
    assert third_party["source_role"] == SourceRole.THIRD_PARTY.value

    nist = enrich_page_metadata(_page("https://www.nist.gov/report"))
    assert nist["source_role"] == SourceRole.GOVERNMENT_OR_STANDARD_BODY.value

    github = enrich_page_metadata(_page("https://github.com/openai/example"))
    assert github["source_role"] == SourceRole.UNKNOWN.value
    assert "publisher" not in github

    unknown = enrich_page_metadata(_page("https://unrecognized.invalid/a"))
    assert unknown["source_role"] == SourceRole.UNKNOWN.value

    conflicting_official = enrich_page_metadata(
        _page("https://docs.aws.amazon.com/story"),
        structured_metadata={"publisher": "Unrelated Publisher"},
    )
    assert conflicting_official["metadata_conflict"] is True
    assert conflicting_official["source_role"] == SourceRole.THIRD_PARTY.value

    generic_org = enrich_page_metadata(_page("https://example.org/story"))
    assert generic_org["source_role"] == SourceRole.UNKNOWN.value

    conflicting_identity = enrich_page_metadata({
        **_page("https://docs.aws.amazon.com/story"),
        "source_owner": "Unrelated Publisher",
    })
    assert conflicting_identity["metadata_conflict"] is True
    assert conflicting_identity["source_role"] == SourceRole.THIRD_PARTY.value


def test_conflicting_dates_are_flagged_and_precedence_is_deterministic():
    enriched = enrich_page_metadata(
        _page(content="Published: May 11, 2026"),
        structured_metadata={"publication_date": "2026-05-10"},
        provider_metadata={"publication_date": "2026-05-12"},
    )
    assert enriched["publication_date"] == "2026-05-10"
    assert enriched["metadata_conflict"] is True
    assert enriched["metadata_provenance"]["publication_date"] == "HTML_STRUCTURED_METADATA"


async def test_metadata_survives_candidate_to_selected_evidence():
    enriched = enrich_page_metadata(
        _page(
            "https://docs.aws.amazon.com/service/guide.html",
            "Article\nPublished: May 10, 2026\nAWS capability details." + "x" * 150,
        )
    )
    compressor = ContextCompressor(
        documents=[enriched], embeddings=None, source_reliability_weight=0,
        prompt_family=SimpleNamespace(pretty_print_docs=lambda docs, limit: "context"),
    )
    result = await compressor.async_get_context("AWS capability")
    selected = result.evidences[0]
    assert selected.publisher == "Amazon Web Services"
    assert selected.source_organization == "Amazon Web Services"
    assert selected.source_role is SourceRole.FIRST_PARTY
    assert selected.publication_date == "2026-05-10"
    assert selected.metadata_provenance.publication_date.value == "HTML_VISIBLE_DATE"


def test_old_evidence_loads_with_unknown_defaults():
    evidence = Evidence.model_validate({
        "evidence_id": "old", "sub_query": "q", "content": "legacy"
    })
    assert evidence.publisher is None
    assert evidence.publication_date is None
    assert evidence.updated_date is None
    assert evidence.source_role is SourceRole.UNKNOWN


def test_first_party_metadata_does_not_bypass_claim_relationship_semantics():
    enriched = enrich_page_metadata(_page("https://docs.aws.amazon.com/a"))
    evidence = Evidence(
        evidence_id="ev", sub_query="q", content="AWS pricing details.", **{
            key: value for key, value in enriched.items()
            if key not in {"url", "title", "raw_content"}
        }, url=enriched["url"], title=enriched["title"]
    )
    aws = register_proposal(_proposal("Amazon Web Services"), "run", [evidence])
    assert aws.items[0].qualifications[0].is_primary_source is True

    microsoft = register_proposal(_proposal("Microsoft"), "run", [evidence])
    assert microsoft.items[0].qualifications[0].is_primary_source is None

    third_party = evidence.model_copy(update={
        "publisher": "Example Media", "source_organization": "Example Media",
        "source_role": SourceRole.THIRD_PARTY,
    })
    media = register_proposal(_proposal("Amazon Web Services"), "run", [third_party])
    assert media.items[0].qualifications[0].is_primary_source is None


def test_verified_old_date_is_not_conflated_with_freshness_and_audit_is_populated():
    evidence = Evidence(
        evidence_id="ev", sub_query="q", content="body", publication_date="2025-01-01"
    )
    plan = register_proposal(ClaimProposal(claims=[]), "run", [evidence])
    assert plan.audit_metadata[0].publication_date == date(2025, 1, 1)
    assert (date(2026, 9, 14) - plan.audit_metadata[0].publication_date).days > 180

    unverified = register_proposal(
        ClaimProposal(claims=[]), "run", [evidence.model_copy(update={"publication_date": None})]
    )
    assert unverified.audit_metadata == []


def test_trace_records_only_bounded_metadata_resolution_counts():
    evidence = Evidence(
        evidence_id="ev", sub_query="q", content="body", publisher="OpenAI",
        publication_date="2026-05-10", source_role=SourceRole.FIRST_PARTY,
    )
    trace = ResearchTraceRecorder(run_id="batch-2", trace_id="batch-2-trace")
    trace.record_evidence_selection(
        EvidenceContext(context="", evidences=[evidence]),
        authority_weight=0.1, similarity_threshold=0.35,
    )
    event = trace.events[-1]
    assert event.publisher_resolved_count == 1
    assert event.publication_date_resolved_count == 1
    assert event.metadata_conflict_count == 0


def test_six_case_saved_evidence_replay_has_real_recoverable_metadata():
    root = Path(__file__).resolve().parents[1]
    result = replay(
        root / "docs" / "v2" / "calibration" / "v2.2.0",
        reference_date=date(2026, 9, 14),
    )
    assert result["input"]["case_count"] == 6
    assert result["input"]["saved_evidence_only"] is True
    assert result["runtime_calls"] == {
        "provider": 0, "search": 0, "development": 0, "holdout": 0
    }
    assert result["before"]["known_publisher"] == 0
    assert result["before"]["known_publication_date"] == 0
    assert result["after"]["known_publisher"] == 18
    assert result["after"]["known_publication_date"] == 1
