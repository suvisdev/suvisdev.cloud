"""랭킹 라우터 — GET /mova/rankings/hot"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from shared.security.require_admin import AdminPrincipal, require_admin
from shared.security.require_user import UserPrincipal, optional_user

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
    """HOT 랭킹 조회 — box_office는 최신 스냅샷, chat_trend("mova 랭킹")는 최근 7일 열람 수를 바로 집계."""
    dto = await use_case.get_hot(source, limit)
    return dto.to_schema()


class MovieViewRequest(BaseModel):
    movie_id: int = Field(ge=1)
    visitor_id: str | None = Field(default=None, max_length=64)


@market_rankings_router.post("/views", status_code=204)
async def record_movie_view(
    req: MovieViewRequest,
    request: Request,
    principal: UserPrincipal | None = Depends(optional_user),
    use_case: RankingsUseCase = Depends(get_rankings_use_case),
) -> Response:
    """영화 상세 열람 1건 — "mova 랭킹"(최근 7일 열람 수)의 신호(2026-10-07).

    무인증: 비로그인 열람도 센다는 사용자 결정이라 인증을 요구할 수 없다. 받는 값은 영화 번호와 클라이언트가
    만든 방문자 UUID뿐(개인정보 없음). 같은 (영화, 사람, 하루)는 한 번만 저장되고 봇 UA는 버려, 한 방문자가
    부풀릴 수 있는 건 영화당 하루 1표다. 로그인이면 토큰의 사용자로 센다(바디 값은 쓰지 않음).
    """
    await use_case.record_view(
        req.movie_id,
        user_id=principal.user_id if principal else None,
        visitor_id=req.visitor_id,
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=204)


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
