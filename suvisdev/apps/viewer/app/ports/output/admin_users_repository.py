from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.admin_users_dto import UserAdminDto


class AdminUsersRepository(ABC):
    @abstractmethod
    async def list_users(self) -> list[UserAdminDto]:
        pass
