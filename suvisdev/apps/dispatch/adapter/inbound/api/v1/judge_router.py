from __future__ import annotations

from fastapi import APIRouter, Depends

from dispatch.adapter.inbound.api.schemas.judge_schema import JudgeIntroduceSchema
from dispatch.app.dtos.judge_dto import JudgeIntroduceResponse
from dispatch.app.ports.input.judge_use_case import JudgeUseCase
from dispatch.dependencies.judge_provider import get_judge_use_case

judge_router = APIRouter(prefix="/judge", tags=["dispatch-judge"])


@judge_router.get("/myself")
async def introduce_myself(
    use_case: JudgeUseCase = Depends(get_judge_use_case),
) -> JudgeIntroduceResponse:
    return await use_case.introduce_myself(JudgeIntroduceSchema(id=6, name="저지 심사"))
