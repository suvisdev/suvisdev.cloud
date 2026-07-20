from __future__ import annotations

import logging
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from viewer.app.ports.input.oauth_login_use_case import OAuthLoginUseCase
from viewer.app.ports.output.oauth_errors import OAuthError
from viewer.dependencies.oauth_login_provider import get_oauth_login_use_case

oauth_router = APIRouter(prefix="/oauth", tags=["oauth"])
logger = logging.getLogger(__name__)

_STATE_COOKIE = "oauth_state"
_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@oauth_router.get("/{provider}/login")
async def oauth_login(
    provider: str,
    use_case: OAuthLoginUseCase = Depends(get_oauth_login_use_case),
) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    try:
        url = use_case.build_authorize_url(provider=provider, state=state)
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    response = RedirectResponse(url=url, status_code=302)
    response.set_cookie(
        _STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax", path="/"
    )
    return response


@oauth_router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str,
    state: str,
    use_case: OAuthLoginUseCase = Depends(get_oauth_login_use_case),
) -> RedirectResponse:
    expected_state = request.cookies.get(_STATE_COOKIE, "")
    if not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="state 값이 일치하지 않습니다 (CSRF 의심).")

    try:
        handoff_code = await use_case.handle_callback(provider=provider, code=code)
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    logger.info("🤖 [OAuthRouter] %s 콜백 완료", provider)
    response = RedirectResponse(
        url=f"{_FRONTEND_URL}/oauth/callback?code={handoff_code}", status_code=302
    )
    response.delete_cookie(_STATE_COOKIE, path="/")
    return response


class OAuthExchangeRequest(BaseModel):
    code: str


class OAuthExchangeResponse(BaseModel):
    id: int
    username: str
    token: str


@oauth_router.post("/exchange", response_model=OAuthExchangeResponse)
async def oauth_exchange(
    payload: OAuthExchangeRequest,
    use_case: OAuthLoginUseCase = Depends(get_oauth_login_use_case),
) -> OAuthExchangeResponse:
    session = use_case.redeem(code=payload.code)
    if session is None:
        raise HTTPException(status_code=400, detail="만료되었거나 이미 사용된 코드입니다.")
    return OAuthExchangeResponse(id=session.user_id, username=session.username, token=session.token)
