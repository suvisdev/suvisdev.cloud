from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.oauth_dto import SessionPayloadDto


class SessionStorePort(ABC):
    """세션 JWT 발급·저장(Redis) 출력 포트."""

    @abstractmethod
    def issue_session(self, *, user_id: int, username: str) -> str:
        """세션 JWT를 발급해 Redis에 저장하고, 프론트로 넘길 1회용 handoff code를 반환한다."""

    @abstractmethod
    def redeem_handoff_code(self, *, code: str) -> SessionPayloadDto | None:
        """handoff code를 1회 소비해 세션 정보를 반환한다. 없거나 만료됐으면 None."""
