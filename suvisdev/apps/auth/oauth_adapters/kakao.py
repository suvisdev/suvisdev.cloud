"""Kakao OAuth 2.0 / OIDC 어댑터 — scope=openid 필요. apps/viewer의 동명 어댑터와 별개로
새로 작성한다(auth-isolation 계약상 viewer.* import 불가)."""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from auth.oauth_adapters import OAuthError, OAuthIdentity

_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_JWKS_URL = "https://kauth.kakao.com/.well-known/jwks.json"
_ISSUER = "https://kauth.kakao.com"

# 발급자 서버와 우리 서버의 시계 차이로 iat가 '미래'로 보여 검증이 실패하지 않게 둔 여유(초).
_CLOCK_LEEWAY_S = 60
# 공개키 조회는 인스턴스를 재사용해 캐시하고(요청마다 새로 받지 않음), 응답 없는 조회에 30초(기본) 묶이지 않게 5초.
_JWKS_CLIENT = PyJWKClient(_JWKS_URL, timeout=5)


class KakaoOAuthAdapter:
    provider_id = "kakao"

    def __init__(self) -> None:
        self._client_id = os.getenv("KAKAO_CLIENT_ID", "")
        self._client_secret = os.getenv("KAKAO_CLIENT_SECRET", "")
        self._redirect_uri = os.getenv("AUTH_KAKAO_REDIRECT_URI", "")

    def build_authorize_url(self, state: str) -> str:
        if not self._client_id or not self._redirect_uri:
            raise OAuthError(
                "KAKAO_CLIENT_ID/AUTH_KAKAO_REDIRECT_URI가 설정되지 않았습니다.", status_code=503
            )
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid",
            "state": state,
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthIdentity:
        if not self._client_id or not self._redirect_uri:
            raise OAuthError("Kakao OAuth 설정이 없습니다.", status_code=503)

        data = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "code": code,
        }
        if self._client_secret:
            data["client_secret"] = self._client_secret

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise OAuthError(f"Kakao 토큰 교환 실패: {resp.text[:200]}", status_code=502)

        id_token = resp.json().get("id_token")
        if not id_token:
            raise OAuthError(
                "Kakao 응답에 id_token이 없습니다 (openid scope 동의가 필요합니다).",
                status_code=502,
            )

        try:
            # 키를 새로 받을 때는 동기 HTTP라 이벤트 루프를 막지 않게 스레드에서 돌린다.
            signing_key = await asyncio.to_thread(_JWKS_CLIENT.get_signing_key_from_jwt, id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=_ISSUER,
                leeway=_CLOCK_LEEWAY_S,
            )
        except jwt.PyJWTError as e:
            raise OAuthError(f"Kakao id_token 검증 실패: {e}", status_code=502) from e

        return OAuthIdentity(
            provider=self.provider_id,
            provider_user_id=claims["sub"],
            email=claims.get("email"),
        )
