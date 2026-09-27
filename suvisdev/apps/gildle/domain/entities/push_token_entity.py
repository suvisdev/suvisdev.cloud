from __future__ import annotations

from dataclasses import dataclass

_PLATFORMS = frozenset({"android", "ios"})


@dataclass(frozen=True, slots=True)
class PushToken:
    """FCM 기기 토큰 — 기기 식별자라 개인정보처럼 다룬다(로그아웃·탈퇴 시 삭제)."""

    id: int | None
    user_id: int
    token: str
    platform: str

    def __post_init__(self) -> None:
        if not self.token.strip():
            raise ValueError("token이 비어 있습니다")
        if self.platform not in _PLATFORMS:
            raise ValueError(f"platform은 android|ios 중 하나여야 합니다: {self.platform!r}")
