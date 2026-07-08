"""사용자 취향 조회 출력 포트 — 콜드스타트 개인화 신호 (DIP)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.user_preference_dto import UserPreferenceDto


class UserPreferenceQueryPort(ABC):
    """추천 콜드스타트용 사용자 취향 조회.

    채팅 영속성(ChatRepositoryPort)과 분리된 read-only 쿼리 포트.
    행동 이력이 없을 때 선언적 취향(preferred_genres)을 폴백 신호로 제공한다.
    """

    @abstractmethod
    async def get_preferences(self, user_id: int) -> UserPreferenceDto:
        """user_id의 선언적 취향(nickname, preferred_genres). 미존재 시 empty()."""
