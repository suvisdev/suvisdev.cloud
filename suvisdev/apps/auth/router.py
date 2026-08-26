from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from auth.kakao_mobile_verifier import KakaoTokenInvalid
from auth.mobile_refresh_store import MobileTokenInvalid
from auth.oauth_adapters import OAuthError
from auth.refresh_store import ReuseDetected
from auth.repository import EmailAlreadyExists
from auth.schemas import (
    KakaoMobileLoginRequest,
    KakaoMobileTokenResponse,
    LoginRequest,
    OAuthExchangeRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
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

_DEFAULT_RETURN_TO = "/test-auth-login/result"
# return_to는 로그인 시작 시점에 쿼리로 들어오는 사용자 입력이라 오픈 리다이렉트로
# 악용될 수 있다 — 알려진 프리픽스만 화이트리스트로 허용하고, 그 외는 실패를
# 알리지 않고(공격 시도 티 내지 않기 위해) 조용히 기본값으로 폴백한다.
_ALLOWED_RETURN_TO_PREFIXES = ("/mova", "/titanic", "/gildle", "/test-auth-login/result")


def _sanitize_return_to(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return _DEFAULT_RETURN_TO
    if not any(value == p or value.startswith(f"{p}/") for p in _ALLOWED_RETURN_TO_PREFIXES):
        return _DEFAULT_RETURN_TO
    return value


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    try:
        return await _service.login_with_password(body.username, body.password, body.aud)
    except InvalidCredentials as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/auth/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest) -> TokenResponse:
    try:
        return await _service.signup(body.email, body.password, body.username, body.aud)
    except EmailAlreadyExists as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


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
async def start_oauth_login(
    provider: str, aud: str, return_to: str | None = None
) -> RedirectResponse:
    try:
        url = _service.start_oauth_login(provider, aud, _sanitize_return_to(return_to))
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/callback/{provider}")
async def oauth_callback(provider: str, code: str, state: str | None = None) -> RedirectResponse:
    """토큰을 URL에 직접 싣지 않고 1회용 handoff code만 실어 프론트로 리다이렉트한다
    (viewer의 oauth_router.py와 동일한 패턴). 프론트는 POST /auth/exchange로 code를
    실제 토큰과 맞바꾼다.

    리다이렉트 목적지는 로그인 시작 시점에 저장해둔 return_to(이미 화이트리스트
    검증됨) — 없으면 기본값(/test-auth-login/result)."""
    try:
        token_response, return_to = await _service.handle_oauth_callback(provider, code, state)
    except OAuthStateInvalid as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OAuthIdentityNotLinked as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e

    handoff_code = _service.create_oauth_handoff(token_response)
    destination = return_to or _DEFAULT_RETURN_TO
    return RedirectResponse(
        url=f"{_FRONTEND_URL}{destination}?code={handoff_code}",
        status_code=302,
    )


@router.post("/auth/exchange", response_model=TokenResponse)
async def oauth_exchange(body: OAuthExchangeRequest) -> TokenResponse:
    token_response = await _service.exchange_handoff(body.code)
    if token_response is None:
        raise HTTPException(status_code=404, detail="handoff code가 없거나 만료되었습니다.")
    return token_response


@router.post("/auth/kakao/mobile", response_model=KakaoMobileTokenResponse)
async def kakao_mobile_login(body: KakaoMobileLoginRequest) -> KakaoMobileTokenResponse:
    """susu(Flutter) 전용 — 클라는 access_token만 보낸다(me() 호출 금지, 검증은 여기서만)."""
    try:
        return await _service.login_with_kakao_mobile(body.access_token)
    except KakaoTokenInvalid as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/auth/mobile/refresh", response_model=TokenResponse)
async def mobile_refresh(body: RefreshRequest) -> TokenResponse:
    try:
        return await _service.mobile_refresh(body.refresh_token)
    except MobileTokenInvalid as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/auth/mobile/logout", status_code=204)
async def mobile_logout(body: RefreshRequest) -> None:
    await _service.mobile_logout(body.refresh_token)


@router.get("/.well-known/jwks.json")
async def jwks() -> dict[str, Any]:
    return _issuer.build_jwks()
