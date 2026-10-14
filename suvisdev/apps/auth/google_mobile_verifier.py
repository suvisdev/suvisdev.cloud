"""구글 모바일 로그인 전용 ID 토큰 검증 — google_sign_in(Flutter)이 준 id_token을 JWKS로 확인한다.

앱은 `serverClientId`에 웹 OAuth 클라이언트 ID(GOOGLE_CLIENT_ID)를 넘기므로 id_token의 aud가
웹 로그인(GoogleOAuthAdapter)과 같다. 클라이언트가 보낸 유저정보는 신뢰하지 않고, 서명이 검증된
클레임만 신뢰 출처로 삼는다(카카오 모바일과 같은 원칙).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


@dataclass(frozen=True)
class GoogleMobileIdentity:
    provider_user_id: str
    email: str | None
    nickname: str | None


class GoogleTokenInvalid(Exception):
    """id_token이 없거나 서명·aud·iss·만료 검증에 실패함."""


class GoogleMobileTokenVerifier:
    def __init__(self) -> None:
        self._client_id = os.getenv("GOOGLE_CLIENT_ID", "")

    async def verify(self, id_token: str) -> GoogleMobileIdentity:
        if not self._client_id:
            raise GoogleTokenInvalid("GOOGLE_CLIENT_ID가 설정되지 않았습니다.")
        try:
            signing_key = PyJWKClient(_JWKS_URL).get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=_ISSUERS,
            )
        except jwt.PyJWTError as e:
            raise GoogleTokenInvalid(f"구글 id_token 검증 실패: {e}") from e
        # 확인되지 않은 이메일은 계정 대조에 쓰지 않는다.
        email = claims.get("email") if claims.get("email_verified") else None
        return GoogleMobileIdentity(
            provider_user_id=claims["sub"], email=email, nickname=claims.get("name")
        )
