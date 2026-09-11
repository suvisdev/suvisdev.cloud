from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time

import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from viewer.app.ports.input.oauth_login_use_case import OAuthLoginUseCase
from viewer.app.ports.output.oauth_errors import OAuthError
from viewer.dependencies.oauth_login_provider import get_oauth_login_use_case

oauth_router = APIRouter(prefix="/oauth", tags=["oauth"])
logger = logging.getLogger(__name__)

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_STATE_MAX_AGE_SECONDS = 600
_STATE_KEY_PREFIX = "viewer:oauth:state:"

_state_client: redis.Redis | None = None


def _state_store() -> redis.Redis:
    global _state_client
    if _state_client is None:
        _state_client = redis.from_url(_REDIS_URL, decode_responses=True)
    return _state_client


def _state_secret() -> bytes:
    # 호출 시점에 읽고 미설정이면 즉시 실패 — 구 버전은 모듈 로드 시
    # `os.getenv("JWT_SECRET", "")`로 조용히 빈 키 HMAC이 되어 누구나 state를
    # 위조할 수 있었다(2026-09-11 리뷰).
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise RuntimeError("JWT_SECRET이 설정되지 않았습니다.")
    return secret.encode()


def _sign_state() -> str:
    """CSRF state를 쿠키 없이 자체 서명해 발급한다 — 브라우저/프록시의 쿠키 유실 문제를 피한다.

    서명과 별개로 nonce를 Redis에 TTL로 적어 두고 콜백에서 1회 소비한다 —
    서명만으로는 10분 내 무한 재사용이 가능해 로그인 CSRF에 쓰일 수 있었다
    (2026-09-11 리뷰; auth 게이트웨이의 OAuthStateStore와 동일 방식).
    """
    nonce = secrets.token_urlsafe(16)
    ts = str(int(time.time()))
    payload = f"{nonce}.{ts}"
    sig = hmac.new(_state_secret(), payload.encode(), hashlib.sha256).hexdigest()
    _state_store().set(f"{_STATE_KEY_PREFIX}{nonce}", "1", ex=_STATE_MAX_AGE_SECONDS)
    return f"{payload}.{sig}"


def _verify_state(state: str) -> bool:
    parts = state.split(".")
    if len(parts) != 3:
        return False
    nonce, ts, sig = parts
    payload = f"{nonce}.{ts}"
    expected_sig = hmac.new(_state_secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return False
    try:
        issued_at = int(ts)
    except ValueError:
        return False
    if time.time() - issued_at > _STATE_MAX_AGE_SECONDS:
        return False
    # 1회 소비 — delete가 1을 돌려줄 때만(존재했고 지금 지웠을 때만) 유효
    return _state_store().delete(f"{_STATE_KEY_PREFIX}{nonce}") == 1


@oauth_router.get("/{provider}/login")
async def oauth_login(
    provider: str,
    use_case: OAuthLoginUseCase = Depends(get_oauth_login_use_case),
) -> RedirectResponse:
    try:
        url = use_case.build_authorize_url(provider=provider, state=_sign_state())
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    return RedirectResponse(url=url, status_code=302)


@oauth_router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    use_case: OAuthLoginUseCase = Depends(get_oauth_login_use_case),
) -> RedirectResponse:
    if not _verify_state(state):
        raise HTTPException(status_code=400, detail="state 값이 유효하지 않습니다 (CSRF 의심).")

    try:
        result = await use_case.handle_callback(provider=provider, code=code)
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    logger.info("🤖 [OAuthRouter] %s 콜백 완료 — kind=%s", provider, result.kind)
    # kind="session": 기존에 연결된 계정 → 바로 로그인.
    # kind="consent_required": 신규 신원 → 프론트가 약관 동의 화면을 먼저 보여줘야 한다.
    return RedirectResponse(
        url=f"{_FRONTEND_URL}/oauth/callback?type={result.kind}&code={result.code}",
        status_code=302,
    )


class OAuthExchangeRequest(BaseModel):
    code: str


class OAuthConsentRequest(BaseModel):
    code: str
    agreed: bool


class OAuthExchangeResponse(BaseModel):
    id: int
    username: str
    nickname: str
    token: str
    role: str


@oauth_router.post("/exchange", response_model=OAuthExchangeResponse)
async def oauth_exchange(
    payload: OAuthExchangeRequest,
    use_case: OAuthLoginUseCase = Depends(get_oauth_login_use_case),
) -> OAuthExchangeResponse:
    session = use_case.redeem(code=payload.code)
    if session is None:
        raise HTTPException(status_code=400, detail="만료되었거나 이미 사용된 코드입니다.")
    return OAuthExchangeResponse(
        id=session.user_id,
        username=session.username,
        nickname=session.nickname,
        token=session.token,
        role=session.role,
    )


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
    return OAuthExchangeResponse(
        id=session.user_id,
        username=session.username,
        nickname=session.nickname,
        token=session.token,
        role=session.role,
    )
