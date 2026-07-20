"""Kakao OAuth 2.0 / OIDC 어댑터 — scope=openid 필요, id_token(JWT)을 JWKS로 검증한다."""

from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from viewer.app.dtos.oauth_dto import OAuthIdentity
from viewer.app.ports.output.oauth_errors import OAuthError
from viewer.app.ports.output.oauth_provider_port import OAuthProviderPort

_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_JWKS_URL = "https://kauth.kakao.com/.well-known/jwks.json"
_ISSUER = "https://kauth.kakao.com"


class KakaoOAuthAdapter(OAuthProviderPort):
    provider_id = "kakao"

    def __init__(self) -> None:
        self._client_id = os.getenv("KAKAO_CLIENT_ID", "")
        # Kakao는 앱 설정에 따라 client_secret이 선택 사항이다.
        self._client_secret = os.getenv("KAKAO_CLIENT_SECRET", "")
        self._redirect_uri = os.getenv("KAKAO_REDIRECT_URI", "")

    def build_authorize_url(self, *, state: str) -> str:
        if not self._client_id or not self._redirect_uri:
            raise OAuthError(
                "KAKAO_CLIENT_ID/KAKAO_REDIRECT_URI가 설정되지 않았습니다.", status_code=503
            )
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid",
            "state": state,
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, *, code: str) -> OAuthIdentity:
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
            signing_key = PyJWKClient(_JWKS_URL).get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=_ISSUER,
            )
        except jwt.PyJWTError as e:
            raise OAuthError(f"Kakao id_token 검증 실패: {e}", status_code=502) from e

        return OAuthIdentity(
            provider=self.provider_id,
            provider_user_id=claims["sub"],
            email=claims.get("email"),
            name=claims.get("nickname") or claims.get("name"),
            # Kakao id_token은 email_verified 클레임을 보장하지 않는다 — 없으면
            # 검증 안 된 것으로 간주(안전한 기본값)해 기존 계정에 자동 연결하지 않는다.
            email_verified=bool(claims.get("email_verified", False)),
        )
