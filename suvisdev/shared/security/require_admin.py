"""RBAC 가드 — RS256(auth 게이트웨이) 또는 HS256(viewer 세션) JWT를 검증하고
role=admin만 통과시킨다.

roles 배열은 로그인 시 서버가 ADMIN_EMAILS 기준으로 산출해 토큰 claim에 넣은
값이다. 클라이언트가 보내는 어떤 값도 신뢰하지 않고, 오직 서명 검증된 JWT의
roles만 본다.

require_user.py와 동일하게 RS256 → HS256 두 발급 경로를 모두 수용한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException
from shared.security.token_verifier import verify_token, verify_viewer_session_token

logger = logging.getLogger(__name__)

_MOVA_AUD = "suvis-mova"


@dataclass(frozen=True)
class AdminPrincipal:
    user_id: int
    username: str


def require_admin(authorization: str | None = Header(default=None)) -> AdminPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    rs_err: str | None = None
    try:
        payload = verify_token(token, aud=_MOVA_AUD)
    except Exception as e:
        rs_err = repr(e)
        try:
            payload = verify_viewer_session_token(token)
        except Exception as e2:
            logger.warning(
                "[require_admin] both verifiers failed | RS256=%s | HS256=%s | token_head=%s",
                rs_err,
                repr(e2),
                token[:24],
            )
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.") from e2

    if "admin" not in payload.roles:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    return AdminPrincipal(user_id=int(payload.sub), username="")
