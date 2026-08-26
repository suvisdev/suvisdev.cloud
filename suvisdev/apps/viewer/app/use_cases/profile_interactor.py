from __future__ import annotations

from viewer.app.dtos.profile_dto import ProfileDto
from viewer.app.ports.input.profile_use_case import ProfileUseCase
from viewer.app.ports.output.avatar_storage import AvatarStorage
from viewer.app.ports.output.profile_repository import ProfileRepository


class ProfileInteractor(ProfileUseCase):
    def __init__(self, repository: ProfileRepository, avatar_storage: AvatarStorage) -> None:
        self._repository = repository
        self._avatar_storage = avatar_storage

    async def get_profile(self, user_id: int) -> ProfileDto | None:
        return self._with_avatar_url(await self._repository.get_profile(user_id))

    async def update_nickname(self, user_id: int, nickname: str) -> ProfileDto | None:
        return self._with_avatar_url(await self._repository.update_nickname(user_id, nickname))

    async def update_preferred_genres(self, user_id: int, genres: list[str]) -> ProfileDto | None:
        return self._with_avatar_url(
            await self._repository.update_preferred_genres(user_id, genres)
        )

    async def upload_avatar(
        self, user_id: int, data: bytes, *, content_type: str, ext: str
    ) -> ProfileDto | None:
        key = await self._avatar_storage.upload(user_id, data, content_type=content_type, ext=ext)
        return self._with_avatar_url(await self._repository.update_avatar_key(user_id, key))

    async def delete_account(self, user_id: int) -> bool:
        return await self._repository.delete_user(user_id)

    def _with_avatar_url(self, dto: ProfileDto | None) -> ProfileDto | None:
        """저장된 key로 표시용 URL을 채운다 — presigned URL은 만료값이라 DB에
        두지 않고 응답을 만들 때마다 발급한다."""
        if dto is None or not dto.avatar_key:
            return dto
        dto.avatar_url = self._avatar_storage.build_url(dto.avatar_key)
        return dto
