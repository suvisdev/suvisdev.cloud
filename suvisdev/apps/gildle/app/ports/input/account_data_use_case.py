from __future__ import annotations

from abc import ABC, abstractmethod


class AccountDataUseCase(ABC):
    """회원 탈퇴 시 gildle이 가진 사용자 데이터(산책 기록·기기 토큰)를 지운다.

    계정(users) 자체는 인증 게이트웨이가 지운다 — 각 앱은 자기 테이블만 책임진다."""

    @abstractmethod
    async def erase(self, user_id: int) -> dict[str, int]: ...
