"""Scraper.run must tolerate None/non-dict gather results.

A single failed worker must not raise TypeError/KeyError when filtering
contents, or every successful scrape in the batch is lost.
"""

from __future__ import annotations

import asyncio
import importlib
import unittest
from unittest.mock import MagicMock


def _load_scraper_module():
    # Use the actual package so URL-security imports and package state stay intact.
    return importlib.import_module("gpt_researcher.scraper.scraper")


class TestScraperRunGuards(unittest.TestCase):
    def test_filters_none_and_non_dict(self):
        mod = _load_scraper_module()
        scraper = mod.Scraper(
            urls=["https://a.example", "https://b.example", "https://c.example"],
            user_agent="ua",
            scraper="bs",
            worker_pool=MagicMock(),
        )

        async def fake_extract(url, session):
            if "a." in url:
                return {"raw_content": "good", "url": url}
            if "b." in url:
                return None
            return "not-a-dict"

        scraper.extract_data_from_url = fake_extract  # type: ignore

        out = asyncio.run(scraper.run())
        self.assertEqual(out, [{"raw_content": "good", "url": "https://a.example"}])

    def test_drops_null_raw_content_dicts(self):
        mod = _load_scraper_module()
        scraper = mod.Scraper(
            urls=["https://a.example"],
            user_agent="ua",
            scraper="bs",
            worker_pool=MagicMock(),
        )

        async def fake_extract(url, session):
            return {"raw_content": None, "url": url}

        scraper.extract_data_from_url = fake_extract  # type: ignore
        out = asyncio.run(scraper.run())
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
