from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.profile_dto import ProfileDto


class ProfileUseCase(ABC):
    """viewer 마이페이지 입력 포트."""

    @abstractmethod
    async def get_profile(self, user_id: int) -> ProfileDto | None:
        pass

    @abstractmethod
    async def update_nickname(self, user_id: int, nickname: str) -> ProfileDto | None:
        pass

    @abstractmethod
    async def update_preferred_genres(self, user_id: int, genres: list[str]) -> ProfileDto | None:
        pass

    @abstractmethod
    async def upload_avatar(
        self, user_id: int, data: bytes, *, content_type: str, ext: str
    ) -> ProfileDto | None:
        pass

    @abstractmethod
    async def delete_account(self, user_id: int) -> bool:
        """회원 탈퇴 — 계정과 CASCADE 데이터 전부 삭제."""
        pass
