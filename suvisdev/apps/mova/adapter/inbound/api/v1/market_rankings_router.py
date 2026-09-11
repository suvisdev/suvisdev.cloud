"""랭킹 라우터 — GET /mova/rankings/hot"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from shared.security.require_admin import AdminPrincipal, require_admin

from mova.adapter.inbound.api.schemas.market_rankings_schema import (
    HotRankingListSchema,
    RefreshRankingResponseSchema,
)
from mova.app.ports.input.market_rankings_use_case import (
    GenerateChatTrendRankingUseCase,
    RankingsUseCase,
)
from mova.dependencies.market_rankings_provider import (
    get_generate_chat_trend_ranking_use_case,
    get_rankings_use_case,
)
from mova.domain.value_objects.market_rankings_vo import RANKING_SOURCE_CHAT_TREND

market_rankings_router = APIRouter(prefix="/rankings", tags=["mova-rankings"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@market_rankings_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="프로듀서 (Producer)")


@market_rankings_router.get("/hot", response_model=HotRankingListSchema)
async def get_hot_rankings(
    source: str = Query("chat_trend", description="chat_trend | box_office | manual"),
    limit: int = Query(10, ge=1, le=50),
    use_case: RankingsUseCase = Depends(get_rankings_use_case),
) -> HotRankingListSchema:
    """HOT 랭킹 조회 (source 별 최신 스냅샷)."""
    dto = await use_case.get_hot(source, limit)
    return dto.to_schema()


@market_rankings_router.post("/refresh", response_model=RefreshRankingResponseSchema)
async def refresh_rankings(
    source: str = Query(RANKING_SOURCE_CHAT_TREND, description="현재 chat_trend만 지원"),
    days: int = Query(7, ge=1, le=90, description="집계 윈도우 (일)"),
    limit: int = Query(10, ge=1, le=50, description="상위 K건"),
    use_case: GenerateChatTrendRankingUseCase = Depends(get_generate_chat_trend_ranking_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> RefreshRankingResponseSchema:
    """chat_trend 랭킹 수동 재집계·스냅샷 저장 (수동 트리거용, admin 전용 —
    2026-09-11 H4: 익명이 스냅샷 delete+insert를 반복 트리거할 수 있었다.
    6시간 주기 스케줄러가 정규 경로이므로 공개일 이유가 없다)."""
    if source != RANKING_SOURCE_CHAT_TREND:
        raise HTTPException(status_code=400, detail="refresh는 source=chat_trend만 지원합니다.")
    saved = await use_case.execute(days=days, limit=limit)
    return RefreshRankingResponseSchema(
        source=RANKING_SOURCE_CHAT_TREND,
        ranked_at=date.today(),
        saved=saved,
    )
