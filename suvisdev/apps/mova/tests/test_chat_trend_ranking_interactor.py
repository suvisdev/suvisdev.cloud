from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.dtos.market_rankings_dto import (  # noqa: E402
    ChatTrendAggRowDto,
    ChatTrendRankingRowDto,
)
from mova.app.use_cases.market_rankings_interactor import (  # noqa: E402
    GenerateChatTrendRankingInteractor,
)
from mova.domain.value_objects.market_rankings_vo import chat_trend_score  # noqa: E402


class _FakeRepository:
    def __init__(self, aggregates: list[ChatTrendAggRowDto]) -> None:
        self._aggregates = aggregates
        self.saved_rows: list[ChatTrendRankingRowDto] | None = None
        self.saved_at: date | None = None
        self.agg_args: tuple[int, int] | None = None

    async def aggregate_chat_trend(self, days: int, limit: int) -> list[ChatTrendAggRowDto]:
        self.agg_args = (days, limit)
        return self._aggregates

    async def save_chat_trend_ranking(
        self,
        rows: list[ChatTrendRankingRowDto],
        ranked_at: date,
    ) -> int:
        self.saved_rows = rows
        self.saved_at = ranked_at
        return len(rows)


class ChatTrendScoreTests(unittest.TestCase):
    def test_click_count_passthrough(self) -> None:
        # 2026-08-13: 클릭만 신호 — score == click_count.
        self.assertEqual(chat_trend_score(5), 5)
        self.assertEqual(chat_trend_score(0), 0)


class GenerateChatTrendRankingInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_ranks_by_click_count_desc(self) -> None:
        aggregates = [
            ChatTrendAggRowDto(movie_id=10, click_count=8),  # score 8
            ChatTrendAggRowDto(movie_id=20, click_count=15),  # score 15
            ChatTrendAggRowDto(movie_id=30, click_count=3),  # score 3
        ]
        repo = _FakeRepository(aggregates)
        interactor = GenerateChatTrendRankingInteractor(repository=repo)

        saved = await interactor.execute(days=7, limit=10)

        self.assertEqual(saved, 3)
        self.assertEqual(repo.agg_args, (7, 10))
        assert repo.saved_rows is not None
        # rank 순서: 15 > 8 > 3 → movie 20, 10, 30
        self.assertEqual([r.movie_id for r in repo.saved_rows], [20, 10, 30])
        self.assertEqual([r.rank for r in repo.saved_rows], [1, 2, 3])
        self.assertEqual([r.score for r in repo.saved_rows], [15, 8, 3])
        # chat_id·badge 는 현재 None, ranked_at 은 오늘
        self.assertTrue(all(r.chat_id is None and r.badge is None for r in repo.saved_rows))
        self.assertEqual(repo.saved_at, date.today())

    async def test_empty_aggregates_skips_save(self) -> None:
        repo = _FakeRepository([])
        interactor = GenerateChatTrendRankingInteractor(repository=repo)

        saved = await interactor.execute(days=7, limit=10)

        self.assertEqual(saved, 0)
        self.assertIsNone(repo.saved_rows)  # save 호출 안 됨


if __name__ == "__main__":
    unittest.main()
