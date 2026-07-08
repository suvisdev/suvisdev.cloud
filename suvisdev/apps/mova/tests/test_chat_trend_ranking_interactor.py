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
    def test_weighted_sum(self) -> None:
        # pick*3 + hit*1
        self.assertEqual(chat_trend_score(pick_count=2, hit_sum=5), 11)
        self.assertEqual(chat_trend_score(pick_count=0, hit_sum=0), 0)


class GenerateChatTrendRankingInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_ranks_by_weighted_score_desc(self) -> None:
        # movie 20: 1*3 + 10 = 13 (최고), movie 10: 5*3 + 1 = 16? → 재계산
        aggregates = [
            ChatTrendAggRowDto(movie_id=10, pick_count=5, hit_sum=1),  # score 16
            ChatTrendAggRowDto(movie_id=20, pick_count=1, hit_sum=10),  # score 13
            ChatTrendAggRowDto(movie_id=30, pick_count=2, hit_sum=2),  # score 8
        ]
        repo = _FakeRepository(aggregates)
        interactor = GenerateChatTrendRankingInteractor(repository=repo)

        saved = await interactor.execute(days=7, limit=10)

        self.assertEqual(saved, 3)
        self.assertEqual(repo.agg_args, (7, 10))
        assert repo.saved_rows is not None
        # rank 순서: 16 > 13 > 8 → movie 10, 20, 30
        self.assertEqual([r.movie_id for r in repo.saved_rows], [10, 20, 30])
        self.assertEqual([r.rank for r in repo.saved_rows], [1, 2, 3])
        self.assertEqual([r.score for r in repo.saved_rows], [16, 13, 8])
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
