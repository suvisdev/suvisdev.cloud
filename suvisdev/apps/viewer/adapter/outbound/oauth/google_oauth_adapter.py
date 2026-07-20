"""Google OAuth 2.0 / OIDC 어댑터 — id_token(JWT)을 JWKS로 검증해 신원을 확인한다."""

from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from viewer.app.dtos.oauth_dto import OAuthIdentity
from viewer.app.ports.output.oauth_errors import OAuthError
from viewer.app.ports.output.oauth_provider_port import OAuthProviderPort

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class GoogleOAuthAdapter(OAuthProviderPort):
    provider_id = "google"

    def __init__(self) -> None:
        self._client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self._client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self._redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")

    def build_authorize_url(self, *, state: str) -> str:
        if not self._client_id or not self._redirect_uri:
            raise OAuthError(
                "GOOGLE_CLIENT_ID/GOOGLE_REDIRECT_URI가 설정되지 않았습니다.", status_code=503
            )
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, *, code: str) -> OAuthIdentity:
        if not self._client_id or not self._client_secret or not self._redirect_uri:
            raise OAuthError("Google OAuth 설정이 없습니다.", status_code=503)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        if resp.status_code != 200:
            raise OAuthError(f"Google 토큰 교환 실패: {resp.text[:200]}", status_code=502)

        id_token = resp.json().get("id_token")
        if not id_token:
            raise OAuthError("Google 응답에 id_token이 없습니다.", status_code=502)

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
            raise OAuthError(f"Google id_token 검증 실패: {e}", status_code=502) from e

        return OAuthIdentity(
            provider=self.provider_id,
            provider_user_id=claims["sub"],
            email=claims.get("email"),
            name=claims.get("name"),
            email_verified=bool(claims.get("email_verified", False)),
        )
