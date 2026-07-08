"""랭킹 Interactor — RankingsUseCase 구현체."""

from __future__ import annotations

from datetime import date

from mova.app.dtos.market_rankings_dto import ChatTrendRankingRowDto, RankingListDto
from mova.app.ports.input.market_rankings_use_case import (
    GenerateChatTrendRankingUseCase,
    RankingsUseCase,
)
from mova.app.ports.output.market_rankings_repository import RankingsRepositoryPort
from mova.domain.value_objects.market_rankings_vo import (
    DEFAULT_CHAT_TREND_LIMIT,
    DEFAULT_CHAT_TREND_WINDOW_DAYS,
    chat_trend_score,
)


class RankingsInteractor(RankingsUseCase):
    def __init__(self, repository: RankingsRepositoryPort) -> None:
        self._repository = repository

    async def get_hot(self, source: str, limit: int) -> RankingListDto:
        return await self._repository.get_hot(source, limit)


class GenerateChatTrendRankingInteractor(GenerateChatTrendRankingUseCase):
    def __init__(self, repository: RankingsRepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self,
        days: int = DEFAULT_CHAT_TREND_WINDOW_DAYS,
        limit: int = DEFAULT_CHAT_TREND_LIMIT,
    ) -> int:
        aggregates = await self._repository.aggregate_chat_trend(days=days, limit=limit)
        if not aggregates:
            return 0

        # 가중 점수 내림차순으로 최종 랭크 부여.
        ranked = sorted(
            aggregates,
            key=lambda a: chat_trend_score(a.pick_count, a.hit_sum),
            reverse=True,
        )
        rows = [
            ChatTrendRankingRowDto(
                rank=position,
                movie_id=agg.movie_id,
                chat_id=None,  # 대표 chat 매핑은 현재 미사용 (rankings.chat_id nullable)
                score=chat_trend_score(agg.pick_count, agg.hit_sum),
                badge=None,
            )
            for position, agg in enumerate(ranked, start=1)
        ]
        return await self._repository.save_chat_trend_ranking(rows, date.today())
