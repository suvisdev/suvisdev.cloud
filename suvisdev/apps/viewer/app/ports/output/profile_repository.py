from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.profile_dto import ProfileDto


class ProfileRepository(ABC):
    """viewer 마이페이지 조회 출력 포트."""

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
    async def update_avatar_key(self, user_id: int, avatar_key: str) -> ProfileDto | None:
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> bool:
        """회원 탈퇴 — users row 삭제. 반환: 실제로 지워졌으면 True.

        연관 데이터(리뷰·와치리스트·대화·취향 벡터·OAuth identities 등)는
        모두 users.id를 ondelete=CASCADE로 참조하므로 자동으로 함께 삭제된다.
        """
        pass
