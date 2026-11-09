"""감정분석 스케줄러 — "실행 불가"와 "지금 할 일 없음"을 구분하는지(2026-10-20 리뷰).

예전에는 처리 0건이 연속 2회면 GPU 유무와 무관하게 루프를 끝내, GPU 환경에서
백로그를 소진하면 이후 새 에디터 리뷰가 재시작 전까지 분석되지 않았다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.scheduler import review_sentiment_scheduler as module  # noqa: E402

_EMPTY = {"succeeded": 0, "failed": 0, "skipped": 0}
_ALL_FAILED = {"succeeded": 0, "failed": 50, "skipped": 0}


class _StopLoopError(Exception):
    """계속 도는 루프를 테스트에서 끊기 위한 신호."""


def _sleep_stopping_after(n: int) -> AsyncMock:
    calls = {"n": 0}

    async def _sleep(_seconds: float) -> None:
        calls["n"] += 1
        if calls["n"] >= n:
            raise _StopLoopError

    return AsyncMock(side_effect=_sleep)


class SentimentSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_gpu_stops_without_running(self) -> None:
        once = AsyncMock(return_value=_EMPTY)
        with (
            patch.object(module, "_gpu_available", return_value=False),
            patch.object(module, "run_sentiment_once", once),
        ):
            await module.run_sentiment_scheduler()
        once.assert_not_awaited()

    async def test_empty_batches_keep_polling(self) -> None:
        once = AsyncMock(return_value=_EMPTY)
        sleep = _sleep_stopping_after(5)
        with (
            patch.object(module, "_gpu_available", return_value=True),
            patch.object(module, "run_sentiment_once", once),
            patch.object(module.asyncio, "sleep", sleep),
            self.assertRaises(_StopLoopError),
        ):
            await module.run_sentiment_scheduler()
        self.assertEqual(once.await_count, 5)

    async def test_new_reviews_after_empty_batches_are_processed(self) -> None:
        once = AsyncMock(side_effect=[_EMPTY, _EMPTY, {"succeeded": 3, "failed": 0, "skipped": 0}])
        with (
            patch.object(module, "_gpu_available", return_value=True),
            patch.object(module, "run_sentiment_once", once),
            patch.object(module.asyncio, "sleep", _sleep_stopping_after(3)),
            self.assertRaises(_StopLoopError),
        ):
            await module.run_sentiment_scheduler()
        self.assertEqual(once.await_count, 3)

    async def test_repeated_total_failure_stops(self) -> None:
        once = AsyncMock(return_value=_ALL_FAILED)
        with (
            patch.object(module, "_gpu_available", return_value=True),
            patch.object(module, "run_sentiment_once", once),
            patch.object(module.asyncio, "sleep", _sleep_stopping_after(10)),
        ):
            await module.run_sentiment_scheduler()
        self.assertEqual(once.await_count, 2)


if __name__ == "__main__":
    unittest.main()
