"""auth 게이트웨이 RS256 토큰 검증 — susu(모바일) 전용 aud.

shared.security만 import한다(apps.auth는 import하지 않음 — auth-isolation 계약).
mova의 apps/mova/dependencies/require_auth.py와 동일 패턴을 이 앱 자체 파일에
독립적으로 둔다(다른 앱들도 각자 자기 파일에 둘 것이라는 관례를 따름).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from shared.security.token_verifier import TokenPayload, verify_token

_SERVICE_AUD = "suvis-susu"


async def get_current_user(request: Request) -> TokenPayload:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 헤더가 없습니다.")
    token = auth_header.removeprefix("Bearer ")
    try:
        return verify_token(token, aud=_SERVICE_AUD)
    except Exception as e:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.") from e
