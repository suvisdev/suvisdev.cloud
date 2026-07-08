from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.mypage_dto import MypageDto


class MypageUseCase(ABC):
    @abstractmethod
    async def get_mypage(self, user_id: int) -> MypageDto:
        pass
