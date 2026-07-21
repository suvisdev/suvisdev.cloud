from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.profile_dto import ProfileDto


class ProfileUseCase(ABC):
    """viewer 마이페이지(GET) 입력 포트."""

    @abstractmethod
    async def get_profile(self, user_id: int) -> ProfileDto | None:
        pass
