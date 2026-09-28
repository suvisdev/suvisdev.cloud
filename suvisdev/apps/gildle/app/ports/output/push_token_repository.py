from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.domain.entities.push_token_entity import PushToken


class PushTokenRepositoryPort(ABC):
    @abstractmethod
    async def upsert(self, token: PushToken) -> PushToken:
        """같은 token 문자열이 있으면 user_id·platform을 갱신한다(기기 재로그인·계정 전환)."""
        ...

    @abstractmethod
    async def delete(self, user_id: int, token: str) -> None:
        """본인 소유 토큰만 지운다. 없으면 조용히 끝난다(멱등)."""
        ...

    @abstractmethod
    async def delete_all_by_user(self, user_id: int) -> int:
        """회원 탈퇴 — 이 사용자의 기기 토큰을 모두 지운다."""
        ...
