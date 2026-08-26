from __future__ import annotations

import os
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.config.api_keys import MissingApiKeyError  # noqa: E402
from ontology.adapter.outbound.scraper import kobis_client  # noqa: E402
from ontology.adapter.outbound.scraper.kobis_scraper import KobisScraper  # noqa: E402
from ontology.test.fakes.fake_crawl_schedule_collabs import FakeVisitedStore  # noqa: E402
from ontology.test.fakes.fake_page_fetcher import FakePageFetcher  # noqa: E402
from ontology.test.fakes.fake_rate_limiter import FakeRateLimiter  # noqa: E402

_FIXTURES = Path(__file__).parent / "fixtures"


def _build_scraper() -> KobisScraper:
    fetcher = FakePageFetcher()
    fetcher.add_rule(
        "searchDailyBoxOfficeList", (_FIXTURES / "kobis_daily_boxoffice.json").read_text()
    )
    fetcher.add_rule("searchMovieInfo", (_FIXTURES / "kobis_movie_detail.json").read_text())
    return KobisScraper(
        fetcher=fetcher, rate_limiter=FakeRateLimiter(), visited_store=FakeVisitedStore()
    )


class KobisScraperTest(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patch = mock.patch.dict(os.environ, {"KOFIC_API_KEY": "fake-kobis-key"})
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()

    def test_maps_boxoffice_and_detail_into_records(self) -> None:
        scraper = _build_scraper()

        records = list(scraper.search("daily:20260715", limit=10))

        self.assertEqual(len(records), 2)
        first = records[0]
        self.assertEqual(first.title, "호프")
        self.assertEqual(first.external_ids, {"kobis_movie_cd": "20183782"})
        self.assertEqual(first.metrics, {"rank": 1.0, "audi_cnt": 152030.0, "audi_acc": 8203941.0})
        self.assertIn("감독: 홍길동", first.content)
        self.assertIn("장르: 드라마, 가족", first.content)

    def test_dedup_key_is_movie_cd_and_target_dt(self) -> None:
        scraper = _build_scraper()

        first_run = list(scraper.search("daily:20260715", limit=10))
        second_run = list(scraper.search("daily:20260715", limit=10))
        different_day = list(scraper.search("daily:20260716", limit=10))

        self.assertEqual(len(first_run), 2)
        self.assertEqual(len(second_run), 0)  # 같은 날짜 재실행 -> dedup
        self.assertEqual(len(different_day), 2)  # 날짜가 다르면 새 레코드

    def test_missing_api_key_raises_clear_error(self) -> None:
        self._env_patch.stop()
        with mock.patch.dict(os.environ, {}, clear=True):
            scraper = _build_scraper()
            with self.assertRaises(MissingApiKeyError) as ctx:
                list(scraper.search("daily:20260715", limit=10))
            self.assertIn("KOFIC_API_KEY", str(ctx.exception))
        self._env_patch.start()


class KobisClientDateTest(unittest.TestCase):
    def test_yesterday_kst_with_injected_clock(self) -> None:
        fixed_now = datetime(2026, 7, 16, 2, 30, tzinfo=UTC)  # UTC 02:30 = KST 11:30
        result = kobis_client.yesterday_kst(now=fixed_now)
        self.assertEqual(result, "20260715")

    def test_yesterday_kst_crosses_midnight_boundary(self) -> None:
        # UTC 23:50(7/15) = KST 08:50(7/16) -> 어제는 7/15
        fixed_now = datetime(2026, 7, 15, 23, 50, tzinfo=UTC)
        result = kobis_client.yesterday_kst(now=fixed_now)
        self.assertEqual(result, "20260715")


if __name__ == "__main__":
    unittest.main()
