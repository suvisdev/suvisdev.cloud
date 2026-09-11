"""감정분석 백필 배치화(2026-09-11) — analyze_missing이 모델을 1회만 올린다.

건당 로드/해제(analyze_one 순회)로 41건 ≈ 30분이던 CLI 경로를 analyze_batch
1회 호출로 바꾼 회귀 고정: ① 배치 호출이 정확히 1번 ② 개별 추론 실패(None)는
failed로 집계하고 나머지는 계속 ③ 모델 로드 실패는 전량 failed.
GPU·실제 모델 없이 fake로 검증한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.use_cases import review_sentiment_backfill_interactor as module  # noqa: E402
from mova.app.use_cases.review_sentiment_backfill_interactor import (  # noqa: E402
    ReviewSentimentBackfillInteractor,
)
from ontology.app.dtos.sentiment_analysis_dto import SentimentResult  # noqa: E402


class _FakeSession:
    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


class _FakeRepo:
    targets: list[tuple[int, str]] = []
    sentiments: list[tuple[int, str, float]] = []

    def __init__(self, *, session: object) -> None:
        pass

    async def list_missing_sentiment(self, limit: int | None) -> list[tuple[int, str]]:
        return type(self).targets[:limit] if limit else list(type(self).targets)

    async def update_sentiment(self, review_id: int, label: str, score: float) -> None:
        type(self).sentiments.append((review_id, label, score))

    async def update_rating_if_null(self, review_id: int, rating: float) -> bool:
        return True


class _FakeAdapter:
    batch_calls: list[list[str]] = []

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult | None]:
        type(self).batch_calls.append(list(texts))
        return [
            SentimentResult(label="긍정", score=0.9),
            None,  # 개별 추론 실패
            SentimentResult(label="부정", score=0.8),
        ][: len(texts)]


class AnalyzeMissingBatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _FakeRepo.targets = [(1, "인생 영화"), (2, "음"), (3, "돈 아깝다")]
        _FakeRepo.sentiments = []
        _FakeAdapter.batch_calls = []
        self.interactor = ReviewSentimentBackfillInteractor(session_factory=_FakeSession)

    async def _run(self) -> dict[str, int]:
        with (
            patch.object(module, "_make_echo_adapter", return_value=_FakeAdapter()),
            patch(
                "mova.adapter.outbound.pg.market_reviews_pg_repository.ReviewsPgRepository",
                _FakeRepo,
            ),
        ):
            return await self.interactor.analyze_missing(limit=None)

    async def test_single_batch_call_with_all_bodies(self) -> None:
        await self._run()
        self.assertEqual(_FakeAdapter.batch_calls, [["인생 영화", "음", "돈 아깝다"]])

    async def test_partial_failure_counts_and_writes(self) -> None:
        stats = await self._run()
        self.assertEqual(stats, {"succeeded": 2, "failed": 1, "skipped": 0})
        self.assertEqual(_FakeRepo.sentiments, [(1, "긍정", 0.9), (3, "부정", 0.8)])

    async def test_load_failure_marks_all_failed(self) -> None:
        with (
            patch.object(module, "_make_echo_adapter", side_effect=RuntimeError("CUDA 없음")),
            patch(
                "mova.adapter.outbound.pg.market_reviews_pg_repository.ReviewsPgRepository",
                _FakeRepo,
            ),
        ):
            stats = await self.interactor.analyze_missing(limit=None)
        self.assertEqual(stats, {"succeeded": 0, "failed": 3, "skipped": 0})

    async def test_no_targets_short_circuits(self) -> None:
        _FakeRepo.targets = []
        stats = await self._run()
        self.assertEqual(stats, {"succeeded": 0, "failed": 0, "skipped": 0})
        self.assertEqual(_FakeAdapter.batch_calls, [])


if __name__ == "__main__":
    unittest.main()
