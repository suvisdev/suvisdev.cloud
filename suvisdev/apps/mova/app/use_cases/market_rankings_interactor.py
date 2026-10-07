"""랭킹 Interactor — RankingsUseCase 구현체."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from shared.user_agent import is_bot_user_agent

from mova.app.dtos.market_rankings_dto import ChatTrendRankingRowDto, RankingListDto
from mova.app.ports.input.market_rankings_use_case import (
    GenerateChatTrendRankingUseCase,
    RankingsUseCase,
)
from mova.app.ports.output.market_rankings_repository import RankingsRepositoryPort
from mova.domain.value_objects.market_rankings_vo import (
    DEFAULT_CHAT_TREND_LIMIT,
    DEFAULT_CHAT_TREND_WINDOW_DAYS,
    RANKING_SOURCE_CHAT_TREND,
    chat_trend_score,
)

_KST = ZoneInfo("Asia/Seoul")


def viewer_key(user_id: int | None, visitor_id: str | None) -> str | None:
    """로그인이면 "u<id>", 아니면 형식이 맞는 방문자 UUID로 "v<uuid>". 둘 다 없으면 None(기록 안 함)."""
    if user_id:
        return f"u{user_id}"
    try:
        return f"v{uuid.UUID(str(visitor_id))}"
    except (ValueError, TypeError):
        return None


class RankingsInteractor(RankingsUseCase):
    def __init__(self, repository: RankingsRepositoryPort) -> None:
        self._repository = repository

    async def get_hot(self, source: str, limit: int) -> RankingListDto:
        # "mova 랭킹"(source=chat_trend, 2026-10-07): 최근 7일 영화 상세 열람 수를 조회 때 바로 집계한다.
        # 스냅샷 스케줄러는 노트북에서만 돌아(집 서버 ENABLE_MOVA_STARTUP=false) 노트북이 밖이면 멈췄다.
        if source == RANKING_SOURCE_CHAT_TREND:
            return await self._repository.get_view_ranking(DEFAULT_CHAT_TREND_WINDOW_DAYS, limit)
        return await self._repository.get_hot(source, limit)

    async def record_view(
        self,
        movie_id: int,
        *,
        user_id: int | None,
        visitor_id: str | None,
        user_agent: str | None,
    ) -> bool:
        key = viewer_key(user_id, visitor_id)
        if key is None or is_bot_user_agent(user_agent):
            return False
        today = datetime.now(UTC).astimezone(_KST).date()
        return await self._repository.record_view(movie_id, key, today)


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

        # 클릭 카운트 내림차순으로 최종 랭크. Repository가 이미 정렬해서 주지만
        # 방어적으로 한 번 더.
        ranked = sorted(
            aggregates,
            key=lambda a: chat_trend_score(a.click_count),
            reverse=True,
        )
        rows = [
            ChatTrendRankingRowDto(
                rank=position,
                movie_id=agg.movie_id,
                chat_id=None,  # 대표 chat 매핑은 현재 미사용 (rankings.chat_id nullable)
                score=chat_trend_score(agg.click_count),
                badge=None,
            )
            for position, agg in enumerate(ranked, start=1)
        ]
        return await self._repository.save_chat_trend_ranking(rows, date.today())
