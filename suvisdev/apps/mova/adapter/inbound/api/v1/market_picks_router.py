"""picks 라우터 — PATCH /mova/picks/{pick_id}/feedback"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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
    use_case: PicksUseCase = Depends(get_picks_use_case),
) -> PickFeedbackSchema:
    """AI 추천에 대한 좋아요/싫어요 피드백 기록.

    보안 TODO(§2 인증 선행): 현재 pick_id만으로 갱신 → 소유권 미검증(IDOR).
    인증 도입 후 요청자 user_id == pick.user_id 확인 필요.
    """
    dto = await use_case.update_feedback(pick_id, body.feedback)
    if not dto.updated:
        raise HTTPException(status_code=404, detail=f"Pick {pick_id} not found")
    return PickFeedbackSchema(pick_id=dto.pick_id, feedback=dto.feedback, updated=dto.updated)
