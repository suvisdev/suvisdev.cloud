from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_db
from viewer.adapter.outbound.pg.login_pg_repository import LoginPgRepository
from viewer.app.ports.input.login_use_case import LoginUseCase
from viewer.app.ports.output.login_repository import LoginRepository
from viewer.app.use_cases.login_interactor import LoginInteractor


def get_login_use_case(db: AsyncSession = Depends(get_viewer_db)) -> LoginUseCase:
    repository: LoginRepository = LoginPgRepository(session=db)
    return LoginInteractor(repository=repository)
