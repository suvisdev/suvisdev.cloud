from __future__ import annotations

import sys
import unittest
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.scraper.kowiki_scraper import KowikiScraper  # noqa: E402
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
    return KowikiScraper(fetcher=fetcher, rate_limiter=FakeRateLimiter(), visited_store=FakeVisitedStore())


class KowikiScraperTest(unittest.TestCase):
    def test_extracts_sections_and_infobox_for_movie_doc(self) -> None:
        scraper = _build_scraper()

        records = list(scraper.search("패터슨", limit=10))

        self.assertEqual(len(records), 2)
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

    def test_person_doc_without_infobox_still_produces_record(self) -> None:
        scraper = _build_scraper()

        records = list(scraper.search("패터슨", limit=10))

        person = records[1]
        self.assertEqual(person.title, "짐 자무시")
        self.assertIsNone(person.infobox)  # 영화 정보 템플릿 없음 — 후처리가 이걸로 필터링
        self.assertIsNone(person.sections)  # "생애"/"필모그래피"는 대상 섹션 목록 밖 — 정상
        self.assertIn("독립영화", person.content)  # lead는 문서 종류 무관하게 항상 채워짐

    def test_serializes_without_error(self) -> None:
        import json

        scraper = _build_scraper()
        for record in scraper.search("패터슨", limit=10):
            line = json.dumps(record.to_json_dict(), ensure_ascii=False)
            json.loads(line)


if __name__ == "__main__":
    unittest.main()
