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

from ontology.adapter.outbound.config.api_keys import MissingApiKeyError  # noqa: E402
from ontology.adapter.outbound.scraper.tmdb_scraper import TmdbScraper  # noqa: E402
from ontology.test.fakes.fake_crawl_schedule_collabs import FakeVisitedStore  # noqa: E402
from ontology.test.fakes.fake_page_fetcher import FakePageFetcher  # noqa: E402
from ontology.test.fakes.fake_rate_limiter import FakeRateLimiter  # noqa: E402

_FIXTURES = Path(__file__).parent / "fixtures"


def _build_scraper() -> TmdbScraper:
    fetcher = FakePageFetcher()
    fetcher.add_rule("search/movie", (_FIXTURES / "tmdb_search.json").read_text())
    fetcher.add_rule("movie/496243", (_FIXTURES / "tmdb_movie_detail.json").read_text())
    return TmdbScraper(
        fetcher=fetcher, rate_limiter=FakeRateLimiter(), visited_store=FakeVisitedStore()
    )


class TmdbScraperTest(unittest.TestCase):
    def test_maps_search_and_detail_into_record(self) -> None:
        with mock.patch.dict(os.environ, {"TMDB_API_KEY": "fake-tmdb-key"}):
            scraper = _build_scraper()
            records = list(scraper.search("기생충", limit=5))

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.title, "기생충")
        self.assertEqual(record.external_ids, {"tmdb_id": "496243"})
        self.assertIn("전원백수인", record.content)

    def test_infobox_key_scheme_matches_kowiki(self) -> None:
        """kowiki infobox와 같은 key 체계(감독/출연/장르/개봉일)를 써야 후처리 매칭이 쉽다."""
        with mock.patch.dict(os.environ, {"TMDB_API_KEY": "fake-tmdb-key"}):
            scraper = _build_scraper()
            record = next(scraper.search("기생충", limit=5))

        assert record.infobox is not None
        self.assertEqual(record.infobox["감독"], "봉준호")
        self.assertEqual(
            record.infobox["출연"], "송강호, 이선균, 조여정, 최우식, 박소담"
        )  # limit 5
        self.assertIn("스릴러", record.infobox["장르"])
        self.assertEqual(record.infobox["개봉일"], "2019-05-30")

    def test_missing_api_key_raises_clear_error(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            scraper = _build_scraper()
            with self.assertRaises(MissingApiKeyError) as ctx:
                list(scraper.search("기생충", limit=5))
            self.assertIn("TMDB_API_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
