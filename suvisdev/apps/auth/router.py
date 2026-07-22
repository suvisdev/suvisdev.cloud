from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from auth.oauth_adapters import OAuthError
from auth.refresh_store import ReuseDetected
from auth.schemas import LoginRequest, OAuthExchangeRequest, RefreshRequest, TokenResponse
from auth.security import JwtAdapter
from auth.services import (
    AuthService,
    InvalidCredentials,
    OAuthIdentityNotLinked,
    OAuthStateInvalid,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_service = AuthService()
_issuer = JwtAdapter()
_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    try:
        return await _service.login_with_password(body.username, body.password, body.aud)
    except InvalidCredentials as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/auth/logout", status_code=204)
async def logout(body: RefreshRequest) -> None:
    await _service.logout(body.refresh_token)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    try:
        return await _service.refresh(body.refresh_token)
    except ReuseDetected as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.get("/auth/login/{provider}")
async def start_oauth_login(provider: str, aud: str) -> RedirectResponse:
    try:
        url = _service.start_oauth_login(provider, aud)
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/callback/{provider}")
async def oauth_callback(provider: str, code: str, state: str | None = None) -> RedirectResponse:
    """토큰을 URL에 직접 싣지 않고 1회용 handoff code만 실어 프론트로 리다이렉트한다
    (viewer의 oauth_router.py와 동일한 패턴). 프론트는 POST /auth/exchange로 code를
    실제 토큰과 맞바꾼다.

    리다이렉트 목적지(/test-auth-login/result)는 이번 라운드 한정 테스트용 — 실제
    통합 시점에 일반화한다."""
    try:
        token_response = await _service.handle_oauth_callback(provider, code, state)
    except OAuthStateInvalid as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OAuthIdentityNotLinked as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e

    handoff_code = _service.create_oauth_handoff(token_response)
    return RedirectResponse(
        url=f"{_FRONTEND_URL}/test-auth-login/result?code={handoff_code}",
        status_code=302,
    )


@router.post("/auth/exchange", response_model=TokenResponse)
async def oauth_exchange(body: OAuthExchangeRequest) -> TokenResponse:
    token_response = await _service.exchange_handoff(body.code)
    if token_response is None:
        raise HTTPException(status_code=404, detail="handoff code가 없거나 만료되었습니다.")
    return token_response


@router.get("/.well-known/jwks.json")
async def jwks() -> dict[str, Any]:
    return _issuer.build_jwks()
