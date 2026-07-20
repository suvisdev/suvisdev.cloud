from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.oauth_dto import OAuthIdentity


class OAuthProviderPort(ABC):
    """OAuth 프로바이더(google/naver/kakao) 출력 포트 — 프로바이더별 어댑터가 구현한다."""

    provider_id: str

    @abstractmethod
    def build_authorize_url(self, *, state: str) -> str:
        pass

    @abstractmethod
    async def exchange_code(self, *, code: str) -> OAuthIdentity:
        pass
