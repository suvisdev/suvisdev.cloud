from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.resource_adapters.dataset.local_jsonl_dataset_repository import (  # noqa: E402
    LocalJsonlDatasetRepository,
)
from ontology.app.dtos.scrape_dto import ScrapedRecord, ScrapeTarget  # noqa: E402
from ontology.app.use_cases.Scraper_interactor import ScrapeDatasetInteractor  # noqa: E402
from ontology.test.fakes.fake_site_scraper import FakeSiteScraper  # noqa: E402

_REQUIRED_FIELDS = {
    "source",
    "keyword",
    "url",
    "title",
    "content",
    "rating",
    "author_hash",
    "scraped_at",
}


class ScrapeDatasetServiceTest(unittest.TestCase):
    def test_scrape_writes_all_records_with_full_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "out.jsonl"
            service = ScrapeDatasetInteractor(
                scraper=FakeSiteScraper(), writer=LocalJsonlDatasetRepository()
            )

            meta = service.run(
                ScrapeTarget(site_id="fake", keyword="패터슨"), limit=10, out_path=out_path
            )

            self.assertEqual(meta.record_count, 10)
            lines = out_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 10)
            for line in lines:
                record = json.loads(line)  # 각 줄이 json.loads 가능해야 한다
                self.assertEqual(_REQUIRED_FIELDS, set(record.keys()))
                self.assertEqual(record["keyword"], "패터슨")

    def test_interrupted_scrape_keeps_partial_file(self) -> None:
        def flaky_search(keyword: str, limit: int) -> Iterator[ScrapedRecord]:
            for i in range(limit):
                if i == 3:
                    raise KeyboardInterrupt
                yield ScrapedRecord(
                    source="fake",
                    keyword=keyword,
                    url=f"https://fake.test/{i}",
                    title=f"title {i}",
                    content="content",
                    rating=None,
                    author_hash="abcd1234",
                    scraped_at=datetime.now(UTC),
                )

        class FlakySiteScraper(FakeSiteScraper):
            def search(self, keyword: str, limit: int) -> Iterator[ScrapedRecord]:
                return flaky_search(keyword, limit)

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "out.jsonl"
            service = ScrapeDatasetInteractor(
                scraper=FlakySiteScraper(), writer=LocalJsonlDatasetRepository()
            )

            with self.assertRaises(KeyboardInterrupt):
                service.run(ScrapeTarget(site_id="fake", keyword="k"), limit=10, out_path=out_path)

            lines = out_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 3)  # i=0,1,2까지 flush된 뒤 i=3에서 중단


if __name__ == "__main__":
    unittest.main()
