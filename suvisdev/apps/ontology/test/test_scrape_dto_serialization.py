from __future__ import annotations

import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.app.dtos.scrape_dto import ScrapedRecord  # noqa: E402


class ScrapedRecordSerializationTest(unittest.TestCase):
    def test_optional_none_fields_are_omitted(self) -> None:
        record = ScrapedRecord(
            source="fake",
            keyword="k",
            url="https://x.test/1",
            title="t",
            content="c",
            author_hash="abcd1234",
            scraped_at=datetime.now(UTC),
        )
        data = record.to_json_dict()

        for optional_field in ("rating", "published_at", "publisher", "summary", "sections", "infobox"):
            self.assertNotIn(optional_field, data)

        line = json.dumps(data, ensure_ascii=False)
        self.assertEqual(json.loads(line), data)  # 각 줄 json.loads 가능

    def test_rss_fields_present_when_set(self) -> None:
        published = datetime(2026, 7, 16, tzinfo=UTC)
        record = ScrapedRecord(
            source="google_news",
            keyword="k",
            url="https://news.google.com/rss/articles/x",
            title="t",
            content="t 요약",
            author_hash="abcd1234",
            scraped_at=datetime.now(UTC),
            published_at=published,
            publisher="연합뉴스",
            summary="요약",
        )
        data = record.to_json_dict()

        self.assertEqual(data["publisher"], "연합뉴스")
        self.assertEqual(data["summary"], "요약")
        self.assertEqual(data["published_at"], published.isoformat())
        for absent_field in ("rating", "sections", "infobox"):
            self.assertNotIn(absent_field, data)

    def test_wiki_fields_present_when_set(self) -> None:
        record = ScrapedRecord(
            source="kowiki",
            keyword="패터슨",
            url="https://ko.wikipedia.org/wiki/패터슨_(영화)",
            title="패터슨 (영화)",
            content="줄거리 서두...",
            author_hash="abcd1234",
            scraped_at=datetime.now(UTC),
            sections={"줄거리": "...", "평가": "..."},
            infobox={"감독": "짐 자무시", "장르": "드라마"},
        )
        data = record.to_json_dict()

        self.assertEqual(data["sections"], {"줄거리": "...", "평가": "..."})
        infobox = data["infobox"]
        assert isinstance(infobox, dict)
        self.assertEqual(infobox["감독"], "짐 자무시")
        json.dumps(data, ensure_ascii=False)  # 직렬화 가능해야 함


if __name__ == "__main__":
    unittest.main()
