"""Naver OAuth 2.0 어댑터.

주의: 네이버는 OIDC id_token(JWT)을 발급하지 않는다 — access_token만 반환하므로
별도 프로필 API(`/v1/nid/me`)를 호출해 신원을 확인한다. Google/Kakao와 달리
이 어댑터만 JWT 검증 단계가 없다.
"""

from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx

from viewer.app.dtos.oauth_dto import OAuthIdentity
from viewer.app.ports.output.oauth_errors import OAuthError
from viewer.app.ports.output.oauth_provider_port import OAuthProviderPort

_AUTH_URL = "https://nid.naver.com/oauth2.0/authorize"
_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
_PROFILE_URL = "https://openapi.naver.com/v1/nid/me"


class NaverOAuthAdapter(OAuthProviderPort):
    provider_id = "naver"

    def __init__(self) -> None:
        self._client_id = os.getenv("NAVER_CLIENT_ID", "")
        self._client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
        self._redirect_uri = os.getenv("NAVER_REDIRECT_URI", "")

    def build_authorize_url(self, *, state: str) -> str:
        if not self._client_id or not self._redirect_uri:
            raise OAuthError(
                "NAVER_CLIENT_ID/NAVER_REDIRECT_URI가 설정되지 않았습니다.", status_code=503
            )
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, *, code: str) -> OAuthIdentity:
        if not self._client_id or not self._client_secret or not self._redirect_uri:
            raise OAuthError("Naver OAuth 설정이 없습니다.", status_code=503)

        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.get(
                _TOKEN_URL,
                params={
                    "grant_type": "authorization_code",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "code": code,
                },
            )
            if token_resp.status_code != 200:
                raise OAuthError(f"Naver 토큰 교환 실패: {token_resp.text[:200]}", status_code=502)
            access_token = token_resp.json().get("access_token")
            if not access_token:
                raise OAuthError("Naver 응답에 access_token이 없습니다.", status_code=502)

            profile_resp = await client.get(
                _PROFILE_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
        if profile_resp.status_code != 200:
            raise OAuthError(f"Naver 프로필 조회 실패: {profile_resp.text[:200]}", status_code=502)

        response = profile_resp.json().get("response") or {}
        provider_user_id = response.get("id")
        if not provider_user_id:
            raise OAuthError("Naver 프로필 응답에 id가 없습니다.", status_code=502)

        return OAuthIdentity(
            provider=self.provider_id,
            provider_user_id=provider_user_id,
            email=response.get("email"),
            name=response.get("name") or response.get("nickname"),
        )
