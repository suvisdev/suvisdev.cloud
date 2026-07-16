from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.resource_adapters.dataset.local_jsonl_dataset_repository import (  # noqa: E402
    LocalJsonlDatasetRepository,
)
from ontology.app.ports.output.crawl_errors import CrawlFetchError  # noqa: E402
from ontology.app.use_cases.custom_url_scrape_interactor import (  # noqa: E402
    CustomUrlScrapeInteractor,
)
from ontology.test.fakes.fake_custom_scrape_collabs import (  # noqa: E402
    FakePageExtractor,
    FakeRobotsChecker,
)
from ontology.test.fakes.fake_page_fetcher import FakePageFetcher  # noqa: E402


class CustomUrlScrapeInteractorTest(unittest.IsolatedAsyncioTestCase):
    async def test_extracts_and_writes_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "out.jsonl"
            fetcher = FakePageFetcher(single_response="<html><body>본문</body></html>")
            extractor = FakePageExtractor(title="예시 페이지", content="추출된 가격: 10000원")
            interactor = CustomUrlScrapeInteractor(
                fetcher=fetcher,
                robots_checker=FakeRobotsChecker(allowed=True),
                extractor=extractor,
                writer=LocalJsonlDatasetRepository(),
            )

            meta = await interactor.run(
                url="https://example.com/product/1",
                instruction="가격만 알려줘",
                out_path=out_path,
            )

            self.assertEqual(meta.record_count, 1)
            line = out_path.read_text(encoding="utf-8").strip()
            record = json.loads(line)
            self.assertEqual(record["url"], "https://example.com/product/1")
            self.assertEqual(record["content"], "추출된 가격: 10000원")
            self.assertEqual(record["title"], "예시 페이지")
            self.assertEqual(extractor.received[0][1], "가격만 알려줘")

    async def test_blocked_by_robots_txt_raises_without_fetching(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "out.jsonl"
            fetcher = FakePageFetcher(single_response="<html></html>")
            interactor = CustomUrlScrapeInteractor(
                fetcher=fetcher,
                robots_checker=FakeRobotsChecker(allowed=False),
                extractor=FakePageExtractor(),
                writer=LocalJsonlDatasetRepository(),
            )

            with self.assertRaises(CrawlFetchError):
                await interactor.run(
                    url="https://blocked.example.com/",
                    instruction="아무거나",
                    out_path=out_path,
                )

            self.assertEqual(fetcher.fetched_urls, [])  # robots 차단이면 페치 자체를 안 함


if __name__ == "__main__":
    unittest.main()
