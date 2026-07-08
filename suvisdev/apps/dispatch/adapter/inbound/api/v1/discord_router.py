from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dispatch.adapter.inbound.api.schemas.discord_schema import (
    DiscordIntroduceSchema,
    DiscordRequest,
    DiscordResponseSchema,
)
from dispatch.app.dtos.discord_dto import DiscordIntroduceResponse
from dispatch.app.ports.input.discord_use_case import DiscordUseCase
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.dependencies.discord_provider import get_discord_use_case

discord_router = APIRouter(prefix="/discord", tags=["dispatch-discord"])


@discord_router.get("/myself")
async def introduce_myself(
    use_case: DiscordUseCase = Depends(get_discord_use_case),
) -> DiscordIntroduceResponse:
    return await use_case.introduce_myself(DiscordIntroduceSchema(id=3, name="Discord 발송"))


@discord_router.post("", response_model=DiscordResponseSchema)
def send_discord(
    req: DiscordRequest,
    use_case: DiscordUseCase = Depends(get_discord_use_case),
) -> DiscordResponseSchema:
    try:
        dto = use_case.send(message=req.message, username=req.username)
    except DispatchError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return DiscordResponseSchema(success=dto.success)
