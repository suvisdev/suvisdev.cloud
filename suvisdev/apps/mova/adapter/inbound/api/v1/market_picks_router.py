"""picks 라우터 — PATCH /mova/picks/{pick_id}/feedback"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from shared.security.require_user import UserPrincipal, require_user

from mova.adapter.inbound.api.schemas.market_picks_schema import (
    PickFeedbackSchema,
    PickFeedbackUpdateSchema,
)
from mova.app.ports.input.market_picks_use_case import PicksUseCase
from mova.dependencies.market_picks_provider import get_picks_use_case

market_picks_router = APIRouter(prefix="/picks", tags=["mova-picks"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@market_picks_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="배급 담당자 (Distributor)")


@market_picks_router.patch("/{pick_id}/feedback", response_model=PickFeedbackSchema)
async def update_pick_feedback(
    pick_id: int,
    body: PickFeedbackUpdateSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: PicksUseCase = Depends(get_picks_use_case),
) -> PickFeedbackSchema:
    """AI 추천에 대한 좋아요/싫어요 피드백 기록 — **본인 pick만**.

    2026-08-07 이전엔 `pick_id`만으로 갱신해 남의 피드백을 바꿀 수 있었다(IDOR,
    코드에 TODO로 남아 있던 항목). 소유권은 리포지토리 WHERE 절에서 함께 판정하며,
    없는 pick과 남의 pick을 구분해 알려주지 않는다(존재 여부 캐내기 방지).

    비로그인 채팅이 만든 익명 pick(`user_id` NULL)은 소유자를 증명할 수 없어
    갱신 대상에서 빠진다 — 프론트에 이 엔드포인트 호출부·프록시가 아예 없어
    (2026-08-07 확인) 실사용 영향은 없다.
    """
    dto = await use_case.update_feedback(pick_id, principal.user_id, body.feedback)
    if not dto.updated:
        raise HTTPException(status_code=404, detail=f"Pick {pick_id} not found")
    return PickFeedbackSchema(pick_id=dto.pick_id, feedback=dto.feedback, updated=dto.updated)
