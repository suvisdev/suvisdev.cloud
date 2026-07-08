from __future__ import annotations

from mova.app.dtos.mypage_dto import MypageDto
from mova.app.ports.input.mypage_use_case import MypageUseCase
from mova.app.ports.output.mypage_repository import MypageRepository


class MypageInteractor(MypageUseCase):
    def __init__(self, repository: MypageRepository) -> None:
        self._repository = repository

    async def get_mypage(self, user_id: int) -> MypageDto:
        return await self._repository.get_mypage(user_id)
