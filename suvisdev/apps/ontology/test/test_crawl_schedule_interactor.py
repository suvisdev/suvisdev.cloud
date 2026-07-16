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
    FakeKeywordRecordingScraper,
    FakeKeywordSource,
    FakeVisitedStore,
)


class CrawlScheduleInteractorTest(unittest.TestCase):
    def _build(
        self, out_dir: Path, *, interval_minutes: int = 60
    ) -> tuple[CrawlScheduleInteractor, FakeCrawlScheduleStatePort, FakeCrawlEventPublisher]:
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

    def test_run_once_ignores_policy_list_and_due_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            visited_store = FakeVisitedStore()
            scraper = FakeDedupingSiteScraper(
                fetcher=None, rate_limiter=None, visited_store=visited_store  # type: ignore[arg-type]
            )
            publisher = FakeCrawlEventPublisher()
            interactor = CrawlScheduleInteractor(
                policies=FakeCrawlPolicyPort([]),  # 정책 목록이 비어있어도 run_once는 무관
                schedule_state=FakeCrawlScheduleStatePort(),
                build_scraper=lambda site_id: scraper,
                writer=LocalJsonlDatasetRepository(),
                event_publisher=publisher,
                output_dir=out_dir,
            )

            meta = interactor.run_once(site_id="fake-dedup", keywords=("k",), limit=3)

            self.assertEqual(meta.record_count, 3)
            self.assertEqual(len(publisher.published), 1)
            self.assertEqual(publisher.published[0].site_id, "fake-dedup")

    def _build_with_keyword_source(
        self, out_dir: Path, *, static_keywords: tuple[str, ...], source: FakeKeywordSource, max_dynamic: int = 20
    ) -> tuple[CrawlScheduleInteractor, FakeKeywordRecordingScraper]:
        scraper = FakeKeywordRecordingScraper()
        policy = CrawlPolicy(
            site_id="fake-recording",
            keywords=static_keywords,
            interval_minutes=60,
            keyword_source="fake_keyword_source",
        )
        interactor = CrawlScheduleInteractor(
            policies=FakeCrawlPolicyPort([policy]),
            schedule_state=FakeCrawlScheduleStatePort(),
            build_scraper=lambda site_id: scraper,
            writer=LocalJsonlDatasetRepository(),
            event_publisher=FakeCrawlEventPublisher(),
            output_dir=out_dir,
            build_keyword_source=lambda source_id: source,
            max_dynamic_keywords=max_dynamic,
        )
        return interactor, scraper

    def test_merges_static_and_dynamic_keywords_deduped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = FakeKeywordSource(titles=["신작A", "신작B", "정적1"])  # "정적1"은 중복
            interactor, scraper = self._build_with_keyword_source(
                Path(tmp), static_keywords=("정적1", "정적2"), source=source
            )

            interactor.run_due_batches(now=datetime(2026, 7, 16, tzinfo=UTC))

            # 정적 2개 + 동적 2개(중복 "정적1" 제외) = 4개, 순서는 정적 먼저
            self.assertEqual(scraper.searched_keywords, ["정적1", "정적2", "신작A", "신작B"])

    def test_dynamic_keywords_capped_at_max(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = FakeKeywordSource(titles=[f"영화{i}" for i in range(30)])
            interactor, scraper = self._build_with_keyword_source(
                Path(tmp), static_keywords=(), source=source, max_dynamic=5
            )

            interactor.run_due_batches(now=datetime(2026, 7, 16, tzinfo=UTC))

            self.assertEqual(len(scraper.searched_keywords), 5)
            self.assertEqual(scraper.searched_keywords, [f"영화{i}" for i in range(5)])

    def test_resolve_failure_keeps_static_keywords_and_continues_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = FakeKeywordSource(raises=True)
            interactor, scraper = self._build_with_keyword_source(
                Path(tmp), static_keywords=("정적1",), source=source
            )

            results = interactor.run_due_batches(now=datetime(2026, 7, 16, tzinfo=UTC))

            self.assertEqual(len(results), 1)  # 배치가 중단되지 않고 끝까지 감
            self.assertEqual(scraper.searched_keywords, ["정적1"])  # 동적 없이 정적만


if __name__ == "__main__":
    unittest.main()
