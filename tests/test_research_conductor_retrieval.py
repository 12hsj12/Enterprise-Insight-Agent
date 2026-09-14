import unittest
from types import SimpleNamespace

from gpt_researcher.skills.researcher import ResearchConductor


class FakeSnippetRetriever:
    def __init__(self, query, query_domains=None):
        self.query = query
        self.query_domains = query_domains or []

    def search(self, max_results=10):
        return [
            {
                "href": "https://example.com/one",
                "body": "A" * 180,
                "published_date": "2026-05-10",
            },
            {
                "href": "https://example.com/two",
                "body": "B" * 220,
            },
        ]


class FakeFullContentRetriever:
    def __init__(self, query, query_domains=None):
        self.query = query
        self.query_domains = query_domains or []

    def search(self, max_results=10):
        return [
            {
                "href": "https://example.com/full",
                "body": "short summary",
                "raw_content": "C" * 500,
            }
        ]


class ResearchConductorRetrievalTests(unittest.IsolatedAsyncioTestCase):
    def make_researcher(self, retriever_class):
        class FakeResearcher:
            def __init__(self):
                self.retrievers = [retriever_class]
                self.cfg = SimpleNamespace(max_search_results_per_query=5)
                self.verbose = False
                self.websocket = None
                self.visited_urls = set()
                self.research_sources = []

            def add_research_sources(self, sources):
                self.research_sources.extend(sources)

        return FakeResearcher()

    async def test_snippet_only_results_are_sent_to_scraper(self):
        researcher = self.make_researcher(FakeSnippetRetriever)
        conductor = ResearchConductor(researcher)

        urls, prefetched, metadata = await conductor._search_relevant_source_urls("rust async runtimes")

        self.assertCountEqual(
            urls,
            ["https://example.com/one", "https://example.com/two"],
        )
        self.assertEqual(prefetched, [])
        self.assertEqual(metadata, {
            "https://example.com/one": {"publication_date": "2026-05-10"}
        })

    async def test_search_metadata_is_merged_after_scraping(self):
        researcher = self.make_researcher(FakeSnippetRetriever)

        class ScraperManager:
            async def browse_urls(self, urls):
                return [
                    {"url": url, "title": "Story", "raw_content": "body" * 50}
                    for url in urls
                ]

        researcher.scraper_manager = ScraperManager()
        researcher.vector_store = None
        conductor = ResearchConductor(researcher)
        pages = await conductor._scrape_data_by_urls("query")
        first = next(page for page in pages if page["url"].endswith("/one"))
        self.assertEqual(first["publication_date"], "2026-05-10")
        self.assertEqual(
            first["metadata_provenance"]["publication_date"],
            "SEARCH_RESULT_METADATA",
        )

    async def test_raw_content_results_stay_prefetched(self):
        researcher = self.make_researcher(FakeFullContentRetriever)
        conductor = ResearchConductor(researcher)

        urls, prefetched, metadata = await conductor._search_relevant_source_urls("pubmed article")

        self.assertEqual(urls, [])
        self.assertEqual(
            prefetched,
            [{"url": "https://example.com/full", "raw_content": "C" * 500}],
        )
        self.assertEqual(metadata, {})


if __name__ == "__main__":
    unittest.main()
