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
        result = await use_case.handle_callback(provider=provider, code=code)
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    logger.info("🤖 [OAuthRouter] %s 콜백 완료 — kind=%s", provider, result.kind)
    # kind="session": 기존에 연결된 계정 → 바로 로그인.
    # kind="consent_required": 신규 신원 → 프론트가 약관 동의 화면을 먼저 보여줘야 한다.
    response = RedirectResponse(
        url=f"{_FRONTEND_URL}/oauth/callback?type={result.kind}&code={result.code}",
        status_code=302,
    )
    response.delete_cookie(_STATE_COOKIE, path="/")
    return response


class OAuthExchangeRequest(BaseModel):
    code: str


class OAuthConsentRequest(BaseModel):
    code: str
    agreed: bool


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


@oauth_router.post("/consent", response_model=OAuthExchangeResponse)
async def oauth_consent(
    payload: OAuthConsentRequest,
    use_case: OAuthLoginUseCase = Depends(get_oauth_login_use_case),
) -> OAuthExchangeResponse:
    """약관 동의 완료(또는 거부) 처리 — agreed=True일 때만 계정을 생성하고 세션을 발급한다."""
    session = await use_case.complete_consent(code=payload.code, agreed=payload.agreed)
    if session is None:
        raise HTTPException(
            status_code=400, detail="만료되었거나 이미 처리된 요청이거나, 동의가 거부됐습니다."
        )
    return OAuthExchangeResponse(id=session.user_id, username=session.username, token=session.token)
