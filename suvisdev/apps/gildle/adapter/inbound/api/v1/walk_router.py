"""산책 기록 라우터 — 전부 로그인 필수 (2026-09-22).

경로 계산(`/routes`)은 비로그인도 쓰지만, 기록은 개인 데이터라 `require_user`로
막는다. 남의 기록 조회는 403이 아니라 404로 응답한다(id 존재 여부를 흘리지 않기
위해서다 — 2026-08-07 mova 마이페이지 IDOR 수정과 같은 기준).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from shared.security.require_user import UserPrincipal, require_user

from gildle.adapter.inbound.api.schemas.walk_schema import (
    WalkCreateSchema,
    WalkDetailSchema,
    WalkStatsSchema,
    WalkSummarySchema,
)
from gildle.app.dtos.walk_dto import WalkCreateCommand, WalkListQuery
from gildle.app.ports.input.walk_use_case import WalkUseCase
from gildle.dependencies.walk_provider import get_walk_use_case

walk_router = APIRouter(prefix="/walks", tags=["gildle-walks"])


@walk_router.post("", response_model=WalkDetailSchema, status_code=status.HTTP_201_CREATED)
async def record_walk(
    payload: WalkCreateSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: WalkUseCase = Depends(get_walk_use_case),
) -> WalkDetailSchema:
    walk = await use_case.record(
        WalkCreateCommand(
            user_id=principal.user_id,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            distance_m=payload.distance_m,
            duration_s=payload.duration_s,
            path=payload.path,
            season_mode=payload.season_mode,
            avg_shade_score=payload.avg_shade_score,
            memo=payload.memo,
        )
    )
    return WalkDetailSchema.of_walk(walk)


@walk_router.get("", response_model=list[WalkSummarySchema])
async def list_walks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: UserPrincipal = Depends(require_user),
    use_case: WalkUseCase = Depends(get_walk_use_case),
) -> list[WalkSummarySchema]:
    rows = await use_case.list_mine(
        WalkListQuery(user_id=principal.user_id, limit=limit, offset=offset)
    )
    return [WalkSummarySchema.of(r) for r in rows]


@walk_router.get("/stats", response_model=WalkStatsSchema)
async def walk_stats(
    principal: UserPrincipal = Depends(require_user),
    use_case: WalkUseCase = Depends(get_walk_use_case),
) -> WalkStatsSchema:
    return WalkStatsSchema.of(await use_case.stats(principal.user_id))


@walk_router.get("/{walk_id}", response_model=WalkDetailSchema)
async def walk_detail(
    walk_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: WalkUseCase = Depends(get_walk_use_case),
) -> WalkDetailSchema:
    return WalkDetailSchema.of_walk(await use_case.detail(walk_id, principal.user_id))


@walk_router.delete("/{walk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_walk(
    walk_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: WalkUseCase = Depends(get_walk_use_case),
) -> None:
    await use_case.remove(walk_id, principal.user_id)
