"""로그인 가드 — auth 게이트웨이가 발급한 RS256 JWT를 검증하고 role과 무관하게
통과시킨다(본인 확인용).

mova/dependencies/require_auth.py의 get_current_user와 같은 검증 로직이지만,
UserPrincipal 인터페이스를 유지해 기존 라우터들이 그대로 쓸 수 있게 감싼다.

과거엔 HS256 + JWT_SECRET을 썼지만(레거시 viewer 로그인 경로), 실서비스에서
발급되는 토큰은 전부 auth 게이트웨이의 RS256이라 이제는 RS256만 검증한다
(2026-08-12 통일).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException
from shared.security.token_verifier import verify_token, verify_viewer_session_token

logger = logging.getLogger(__name__)

_MOVA_AUD = "suvis-mova"


@dataclass(frozen=True)
class UserPrincipal:
    user_id: int
    username: str
    role: str = "user"


def require_user(authorization: str | None = Header(default=None)) -> UserPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    # 두 발급 경로를 모두 수용: (1) auth 게이트웨이 RS256+aud, (2) viewer 세션 HS256.
    # 2026-08-13: mova 인증 라우터 전체가 401나는 이슈 진단 중 — 어느 검증기가
    # 왜 실패했는지 로그로 남긴다(원인 발견 후 로그는 유지, 소음 아님).
    rs_err: str | None = None
    try:
        payload = verify_token(token, aud=_MOVA_AUD)
    except Exception as e:
        rs_err = repr(e)
        try:
            payload = verify_viewer_session_token(token)
        except Exception as e2:
            logger.warning(
                "[require_user] both verifiers failed | RS256=%s | HS256=%s | token_head=%s",
                rs_err,
                repr(e2),
                token[:24],
            )
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.") from e2

    # RS256 토큰엔 username이 안 들어 있음. 라우터에서 실제로 username을 쓰는
    # 코드가 없어 빈 문자열로 둔다(있으면 /mova/whoami로 별도 조회).
    role = "admin" if "admin" in payload.roles else "user"
    return UserPrincipal(user_id=int(payload.sub), username="", role=role)


def optional_user(authorization: str | None = Header(default=None)) -> UserPrincipal | None:
    """로그인해도 되고 안 해도 되는 엔드포인트용 — 토큰이 있으면 검증해서 신원을
    주고, 없으면 `None`(익명)을 준다.

    `/mova/chat`처럼 **비로그인 사용을 의도적으로 허용**하지만, 로그인한 요청은
    본인으로만 처리해야 하는 곳에 쓴다.

    **토큰이 붙었는데 유효하지 않으면 익명으로 강등하지 않고 401을 낸다** —
    만료된 세션을 조용히 익명 처리하면 사용자는 개인화가 왜 끊겼는지 알 수 없다.
    """
    if authorization is None or not authorization.strip():
        return None
    return require_user(authorization)
