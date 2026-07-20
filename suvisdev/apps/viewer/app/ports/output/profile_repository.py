from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.profile_dto import ProfileDto


class ProfileRepository(ABC):
    """viewer 마이페이지 조회 출력 포트."""

    @abstractmethod
    async def get_profile(self, user_id: int) -> ProfileDto | None:
        pass
