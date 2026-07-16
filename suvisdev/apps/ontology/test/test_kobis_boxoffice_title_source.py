from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.scraper.kobis_boxoffice_title_source import (  # noqa: E402
    KobisBoxofficeTitleSource,
)
from ontology.test.fakes.fake_page_fetcher import FakePageFetcher  # noqa: E402
from ontology.test.fakes.fake_rate_limiter import FakeRateLimiter  # noqa: E402

_FIXTURES = Path(__file__).parent / "fixtures"


class KobisBoxofficeTitleSourceTest(unittest.TestCase):
    def test_resolve_returns_boxoffice_titles(self) -> None:
        fetcher = FakePageFetcher(
            single_response=(_FIXTURES / "kobis_daily_boxoffice.json").read_text()
        )
        source = KobisBoxofficeTitleSource(fetcher=fetcher, rate_limiter=FakeRateLimiter())

        with mock.patch.dict(os.environ, {"KOFIC_API_KEY": "fake-key"}):
            titles = source.resolve()

        self.assertEqual(titles, ["호프", "설국열차 리마스터"])


if __name__ == "__main__":
    unittest.main()
