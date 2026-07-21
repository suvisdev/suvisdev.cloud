from __future__ import annotations

from viewer.app.dtos.admin_users_dto import UserAdminDto
from viewer.app.ports.input.admin_users_use_case import AdminUsersUseCase
from viewer.app.ports.output.admin_users_repository import AdminUsersRepository


class AdminUsersInteractor(AdminUsersUseCase):
    def __init__(self, repository: AdminUsersRepository) -> None:
        self._repository = repository

    async def list_users(self) -> list[UserAdminDto]:
        return await self._repository.list_users()
