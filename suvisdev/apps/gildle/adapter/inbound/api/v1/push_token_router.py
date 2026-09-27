"""FCM 토큰 등록·해제 (2026-09-27). 로그인 필수 — 토큰은 기기 식별자다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from shared.security.require_user import UserPrincipal, require_user

from gildle.adapter.inbound.api.schemas.push_token_schema import (
    PushTokenDeleteSchema,
    PushTokenSchema,
)
from gildle.app.errors import PushTokenValidationError
from gildle.app.ports.input.push_token_use_case import PushTokenUseCase
from gildle.dependencies.push_token_provider import get_push_token_use_case

push_token_router = APIRouter(prefix="/push-tokens", tags=["gildle-push"])


@push_token_router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def register_push_token(
    payload: PushTokenSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: PushTokenUseCase = Depends(get_push_token_use_case),
) -> None:
    try:
        await use_case.register(principal.user_id, payload.token, payload.platform)
    except PushTokenValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@push_token_router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_push_token(
    payload: PushTokenDeleteSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: PushTokenUseCase = Depends(get_push_token_use_case),
) -> None:
    await use_case.unregister(principal.user_id, payload.token)
