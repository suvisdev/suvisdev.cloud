"""사용자 취향 DTO — 콜드스타트 개인화 신호."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserPreferenceDto:
    """로그인 사용자의 선언적 취향 (users 프로필).

    행동 이력이 없는 콜드스타트 상황에서 추천 개인화의 폴백 신호로 쓰인다.
    """

    nickname: str | None
    preferred_genres: list[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> UserPreferenceDto:
        """사용자 미존재·비로그인 — 신호 없음."""
        return cls(nickname=None, preferred_genres=[])

    def has_genre_signal(self) -> bool:
        """선언된 선호 장르가 있어 콜드스타트 개인화가 가능한지."""
        return bool(self.preferred_genres)
