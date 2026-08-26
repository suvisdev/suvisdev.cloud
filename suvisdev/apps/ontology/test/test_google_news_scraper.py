from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.scraper.google_news_scraper import GoogleNewsScraper  # noqa: E402
from ontology.test.fakes.fake_crawl_schedule_collabs import FakeVisitedStore  # noqa: E402
from ontology.test.fakes.fake_page_fetcher import FakePageFetcher  # noqa: E402
from ontology.test.fakes.fake_rate_limiter import FakeRateLimiter  # noqa: E402

_FIXTURE = (Path(__file__).parent / "fixtures" / "google_news_sample.xml").read_text(
    encoding="utf-8"
)


class GoogleNewsScraperTest(unittest.TestCase):
    def _build(self) -> tuple[GoogleNewsScraper, FakeVisitedStore, FakeRateLimiter]:
        fetcher = FakePageFetcher(single_response=_FIXTURE)
        visited = FakeVisitedStore()
        rate_limiter = FakeRateLimiter()
        scraper = GoogleNewsScraper(
            fetcher=fetcher, rate_limiter=rate_limiter, visited_store=visited
        )
        return scraper, visited, rate_limiter

    def test_parses_title_link_published_publisher_summary(self) -> None:
        scraper, _visited, rate_limiter = self._build()

        records = list(scraper.search("패터슨", limit=10))

        self.assertEqual(len(records), 2)
        first = records[0]
        self.assertEqual(first.title, "패터슨 재개봉, 짐 자무시 감성 그대로 - 씨네21")
        self.assertEqual(
            first.url, "https://news.google.com/rss/articles/CBMiEXNhbXBsZS1saW5rLTE?oc=5"
        )
        self.assertEqual(first.publisher, "씨네21")
        self.assertIsNotNone(first.published_at)
        assert first.published_at is not None
        self.assertEqual(first.published_at.year, 2026)
        self.assertEqual(first.published_at.month, 7)
        self.assertEqual(first.published_at.day, 15)
        self.assertIsNotNone(first.summary)
        assert first.summary is not None
        self.assertIn("패터슨 재개봉", first.summary)
        self.assertNotIn("<a", first.summary)  # HTML 태그 제거됐는지
        self.assertNotIn("<font", first.summary)
        self.assertIn(first.title, first.content)  # content = title + summary

        self.assertEqual(rate_limiter.acquired_domains, ["news.google.com"])  # 피드 1회 fetch

    def test_limit_caps_item_count(self) -> None:
        scraper, _visited, _rl = self._build()

        records = list(scraper.search("패터슨", limit=1))

        self.assertEqual(len(records), 1)

    def test_second_run_over_same_feed_yields_nothing_new(self) -> None:
        scraper, visited, _rl = self._build()

        first = list(scraper.search("패터슨", limit=10))
        self.assertEqual(len(first), 2)

        second = list(scraper.search("패터슨", limit=10))
        self.assertEqual(len(second), 0)  # dedup — 같은 피드, 새 기사 없음


if __name__ == "__main__":
    unittest.main()
