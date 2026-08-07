from __future__ import annotations

from viewer.app.dtos.profile_dto import ProfileDto
from viewer.app.ports.input.profile_use_case import ProfileUseCase
from viewer.app.ports.output.profile_repository import ProfileRepository


class ProfileInteractor(ProfileUseCase):
    def __init__(self, repository: ProfileRepository) -> None:
        self._repository = repository

    async def get_profile(self, user_id: int) -> ProfileDto | None:
        return await self._repository.get_profile(user_id)

    async def update_nickname(self, user_id: int, nickname: str) -> ProfileDto | None:
        return await self._repository.update_nickname(user_id, nickname)

    async def update_preferred_genres(
        self, user_id: int, genres: list[str]
    ) -> ProfileDto | None:
        return await self._repository.update_preferred_genres(user_id, genres)
