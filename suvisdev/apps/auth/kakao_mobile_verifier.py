"""카카오 모바일 로그인 전용 access_token 검증 — kapi.kakao.com/v2/user/me 호출.

웹 로그인의 KakaoOAuthAdapter(oauth_adapters/kakao.py)는 authorization code +
OIDC id_token(JWKS 검증) 방식이라 모바일(kakao_flutter_sdk가 access_token을 직접
반환)과 흐름이 다르다 — 그래서 별도 어댑터로 분리한다. 클라이언트가 보낸 유저정보는
신뢰하지 않고, 이 어댑터의 kapi 응답만을 신뢰 출처로 삼는다.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

_ME_URL = "https://kapi.kakao.com/v2/user/me"


@dataclass(frozen=True)
class KakaoMobileIdentity:
    provider_user_id: str
    email: str | None
    nickname: str | None


class KakaoTokenInvalid(Exception):
    """access_token이 없거나 kapi가 거부함(만료/위조 등)."""


class KakaoMobileTokenVerifier:
    async def verify(self, access_token: str) -> KakaoMobileIdentity:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _ME_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
        if resp.status_code != 200:
            raise KakaoTokenInvalid(f"카카오 access_token 검증 실패: {resp.text[:200]}")

        body = resp.json()
        kakao_account = body.get("kakao_account") or {}
        profile = kakao_account.get("profile") or {}
        return KakaoMobileIdentity(
            provider_user_id=str(body["id"]),
            email=kakao_account.get("email"),
            nickname=profile.get("nickname"),
        )
