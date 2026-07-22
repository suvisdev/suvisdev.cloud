from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from auth.oauth_adapters import OAuthError
from auth.refresh_store import ReuseDetected
from auth.schemas import LoginRequest, RefreshRequest, TokenResponse
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


@router.get("/auth/callback/{provider}", response_model=TokenResponse)
async def oauth_callback(provider: str, code: str, state: str | None = None) -> TokenResponse:
    try:
        return await _service.handle_oauth_callback(provider, code, state)
    except OAuthStateInvalid as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OAuthIdentityNotLinked as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e


@router.get("/.well-known/jwks.json")
async def jwks() -> dict[str, Any]:
    return _issuer.build_jwks()
