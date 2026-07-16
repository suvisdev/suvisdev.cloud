from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.resource_adapters.dataset.local_jsonl_dataset_repository import (  # noqa: E402
    LocalJsonlDatasetRepository,
)
from ontology.app.dtos.crawl_schedule_dto import CrawlPolicy  # noqa: E402
from ontology.app.use_cases.Crawler_interactor import CrawlScheduleInteractor  # noqa: E402
from ontology.test.fakes.fake_crawl_schedule_collabs import (  # noqa: E402
    FakeCrawlEventPublisher,
    FakeCrawlPolicyPort,
    FakeCrawlScheduleStatePort,
    FakeDedupingSiteScraper,
    FakeVisitedStore,
)


class CrawlScheduleInteractorTest(unittest.TestCase):
    def _build(self, out_dir: Path, *, interval_minutes: int = 60):
        visited_store = FakeVisitedStore()
        scraper = FakeDedupingSiteScraper(
            fetcher=None, rate_limiter=None, visited_store=visited_store  # type: ignore[arg-type]
        )
        policy = CrawlPolicy(
            site_id="fake-dedup", keywords=("k",), interval_minutes=interval_minutes
        )
        state = FakeCrawlScheduleStatePort()
        publisher = FakeCrawlEventPublisher()
        interactor = CrawlScheduleInteractor(
            policies=FakeCrawlPolicyPort([policy]),
            schedule_state=state,
            build_scraper=lambda site_id: scraper,
            writer=LocalJsonlDatasetRepository(),
            event_publisher=publisher,
            output_dir=out_dir,
        )
        return interactor, state, publisher

    def test_second_run_collects_no_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            interactor, state, publisher = self._build(out_dir, interval_minutes=1)
            t0 = datetime(2026, 7, 16, tzinfo=UTC)

            first = interactor.run_due_batches(now=t0)
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0].record_count, 3)

            second = interactor.run_due_batches(now=t0 + timedelta(minutes=5))
            self.assertEqual(second[0].record_count, 0)  # dedup — 새로 생긴 게 없음

            lines = Path(first[0].path).read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 3)  # append 2번 했지만 중복 없이 3줄 그대로
            for line in lines:
                json.loads(line)

            self.assertEqual(len(publisher.published), 2)  # 매 실행마다 발행(0건이어도)

    def test_skips_when_not_due_yet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            interactor, state, publisher = self._build(Path(tmp), interval_minutes=60)
            t0 = datetime(2026, 7, 16, tzinfo=UTC)

            interactor.run_due_batches(now=t0)
            self.assertEqual(len(publisher.published), 1)

            interactor.run_due_batches(now=t0 + timedelta(minutes=30))
            self.assertEqual(len(publisher.published), 1)  # 아직 60분 안 지남 — 스킵

            interactor.run_due_batches(now=t0 + timedelta(minutes=61))
            self.assertEqual(len(publisher.published), 2)  # 지남 — 다시 실행


if __name__ == "__main__":
    unittest.main()
