from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_db
from viewer.adapter.outbound.pg.admin_users_pg_repository import AdminUsersPgRepository
from viewer.app.ports.input.admin_users_use_case import AdminUsersUseCase
from viewer.app.ports.output.admin_users_repository import AdminUsersRepository
from viewer.app.use_cases.admin_users_interactor import AdminUsersInteractor


def get_admin_users_use_case(db: AsyncSession = Depends(get_viewer_db)) -> AdminUsersUseCase:
    repository: AdminUsersRepository = AdminUsersPgRepository(session=db)
    return AdminUsersInteractor(repository=repository)
