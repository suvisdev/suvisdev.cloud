from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.oauth_dto import OAuthIdentity


class PendingIdentityRepository(ABC):
    """약관 동의 전 신규 OAuth 신원의 임시 보관소 — 동의 완료 전까지 users에 만들지 않는다."""

    @abstractmethod
    def save_pending(self, identity: OAuthIdentity) -> str:
        """대기 코드를 발급해 신원을 임시 저장한다."""

    @abstractmethod
    def pop_pending(self, *, code: str) -> OAuthIdentity | None:
        """대기 코드를 1회 소비해 신원을 반환한다. 없거나 만료됐으면 None."""
