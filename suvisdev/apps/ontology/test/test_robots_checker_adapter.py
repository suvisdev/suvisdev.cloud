from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.http.robots_checker_adapter import (  # noqa: E402
    HttpxRobotsCheckerAdapter,
)
from ontology.app.ports.output.crawl_errors import CrawlFetchError  # noqa: E402
from ontology.app.ports.output.page_fetcher_port import PageFetcherPort  # noqa: E402
from ontology.test.fakes.fake_page_fetcher import FakePageFetcher  # noqa: E402


class _AlwaysFailFetcher(PageFetcherPort):
    def fetch(self, url: str) -> str:
        raise CrawlFetchError("404", status_code=404)


class HttpxRobotsCheckerAdapterTest(unittest.TestCase):
    def test_disallows_when_robots_txt_blocks_all(self) -> None:
        fetcher = FakePageFetcher(single_response="User-agent: *\nDisallow: /\n")
        checker = HttpxRobotsCheckerAdapter(fetcher=fetcher)

        self.assertFalse(checker.is_allowed("https://blocked.example.com/page"))

    def test_allows_when_robots_txt_permits(self) -> None:
        fetcher = FakePageFetcher(single_response="User-agent: *\nAllow: /\n")
        checker = HttpxRobotsCheckerAdapter(fetcher=fetcher)

        self.assertTrue(checker.is_allowed("https://open.example.com/page"))

    def test_fails_open_when_robots_txt_unreachable(self) -> None:
        checker = HttpxRobotsCheckerAdapter(fetcher=_AlwaysFailFetcher())

        self.assertTrue(checker.is_allowed("https://no-robots.example.com/page"))

    def test_disallows_specific_path_only(self) -> None:
        fetcher = FakePageFetcher(single_response="User-agent: *\nDisallow: /admin/\n")
        checker = HttpxRobotsCheckerAdapter(fetcher=fetcher)

        self.assertFalse(checker.is_allowed("https://mixed.example.com/admin/secret"))
        self.assertTrue(checker.is_allowed("https://mixed.example.com/public"))


if __name__ == "__main__":
    unittest.main()
