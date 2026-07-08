"""chat_trend 랭킹 자동 갱신 스케줄러 — lifespan 백그라운드 루프.

수동 트리거(POST /mova/rankings/refresh)와 동일한 유스케이스를 6시간 간격으로 호출한다.
인바운드 어댑터로서 요청 스코프 밖에서 세션을 직접 만들어 유스케이스를 구동한다.
"""

from __future__ import annotations

import asyncio
import logging

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from mova.adapter.outbound.pg.market_rankings_pg_repository import RankingsPgRepository
from mova.app.use_cases.market_rankings_interactor import (
    GenerateChatTrendRankingInteractor,
)
from mova.domain.value_objects.market_rankings_vo import (
    DEFAULT_CHAT_TREND_LIMIT,
    DEFAULT_CHAT_TREND_WINDOW_DAYS,
)

logger = logging.getLogger(__name__)

CHAT_TREND_REFRESH_INTERVAL_SECONDS = 6 * 60 * 60  # 6시간


async def _refresh_once() -> None:
    session_factory = get_mova_session_factory()
    async with session_factory() as session:
        repository = RankingsPgRepository(session=session)
        interactor = GenerateChatTrendRankingInteractor(repository=repository)
        saved = await interactor.execute(
            days=DEFAULT_CHAT_TREND_WINDOW_DAYS,
            limit=DEFAULT_CHAT_TREND_LIMIT,
        )
    logger.info("[rankings-scheduler] chat_trend 갱신 완료 — saved=%s", saved)


async def run_chat_trend_scheduler() -> None:
    """6시간 간격으로 chat_trend 랭킹을 재집계·저장한다.

    개별 실패로 루프가 죽지 않도록 예외를 잡아 로깅만 하고 다음 주기로 넘어간다.
    앱 종료 시 task.cancel()이 asyncio.sleep에 CancelledError를 던져 루프가 끝난다.
    """
    while True:
        try:
            await _refresh_once()
        except Exception as e:
            logger.warning("[rankings-scheduler] chat_trend 갱신 실패: %s", e)
        await asyncio.sleep(CHAT_TREND_REFRESH_INTERVAL_SECONDS)
