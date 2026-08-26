from __future__ import annotations

import sys
import unittest
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.scraper.kowiki_scraper import (  # noqa: E402
    KowikiScraper,
    _movie_query,
)
from ontology.test.fakes.fake_crawl_schedule_collabs import FakeVisitedStore  # noqa: E402
from ontology.test.fakes.fake_page_fetcher import FakePageFetcher  # noqa: E402
from ontology.test.fakes.fake_rate_limiter import FakeRateLimiter  # noqa: E402

_FIXTURES = Path(__file__).parent / "fixtures"


def _build_scraper() -> KowikiScraper:
    fetcher = FakePageFetcher()
    fetcher.add_rule("list=search", (_FIXTURES / "kowiki_search.json").read_text(encoding="utf-8"))
    fetcher.add_rule(
        f"page={quote('패터슨 (영화)')}",
        (_FIXTURES / "kowiki_parse_movie.json").read_text(encoding="utf-8"),
    )
    fetcher.add_rule(
        f"page={quote('짐 자무시')}",
        (_FIXTURES / "kowiki_parse_person.json").read_text(encoding="utf-8"),
    )
    return KowikiScraper(
        fetcher=fetcher, rate_limiter=FakeRateLimiter(), visited_store=FakeVisitedStore()
    )


def _build_odyssey_scraper() -> KowikiScraper:
    fetcher = FakePageFetcher()
    fetcher.add_rule(
        "list=search",
        (_FIXTURES / "kowiki_search_odyssey.json").read_text(encoding="utf-8"),
    )
    fetcher.add_rule(
        f"page={quote('오디세이 (영화)')}",
        (_FIXTURES / "kowiki_parse_odyssey_movie.json").read_text(encoding="utf-8"),
    )
    fetcher.add_rule(
        f"page={quote('오디세이아')}",
        (_FIXTURES / "kowiki_parse_odyssey_epic.json").read_text(encoding="utf-8"),
    )
    return KowikiScraper(
        fetcher=fetcher, rate_limiter=FakeRateLimiter(), visited_store=FakeVisitedStore()
    )


class KowikiScraperTest(unittest.TestCase):
    def test_extracts_sections_and_infobox_for_movie_doc(self) -> None:
        scraper = _build_scraper()

        records = list(scraper.search("패터슨", limit=10))

        self.assertEqual(len(records), 1)
        movie = records[0]
        self.assertEqual(movie.title, "패터슨 (영화)")
        self.assertIn("짐 자무시", movie.content)
        self.assertIsNotNone(movie.sections)
        assert movie.sections is not None
        self.assertIn("줄거리", movie.sections)
        self.assertIn("버스 운전사", movie.sections["줄거리"])
        self.assertIn("평가", movie.sections)
        self.assertIsNotNone(movie.infobox)
        assert movie.infobox is not None
        self.assertEqual(movie.infobox["감독"], "짐 자무시")
        self.assertEqual(movie.infobox["장르"], "드라마")

    def test_person_doc_without_infobox_is_skipped(self) -> None:
        scraper = _build_scraper()

        records = list(scraper.search("패터슨", limit=10))

        titles = [r.title for r in records]
        self.assertNotIn("짐 자무시", titles)

    def test_odyssey_filters_epic_keeps_movie(self) -> None:
        scraper = _build_odyssey_scraper()

        records = list(scraper.search("오디세이", limit=10))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].title, "오디세이 (영화)")
        assert records[0].infobox is not None
        self.assertEqual(records[0].infobox["감독"], "크리스토퍼 놀란")
        self.assertIn("줄거리", records[0].sections or {})

    def test_movie_query_appends_suffix(self) -> None:
        self.assertEqual(_movie_query("오디세이"), "오디세이 (영화)")
        self.assertEqual(_movie_query("패터슨 (영화)"), "패터슨 (영화)")

    def test_serializes_without_error(self) -> None:
        import json

        scraper = _build_scraper()
        for record in scraper.search("패터슨", limit=10):
            line = json.dumps(record.to_json_dict(), ensure_ascii=False)
            json.loads(line)


if __name__ == "__main__":
    unittest.main()
