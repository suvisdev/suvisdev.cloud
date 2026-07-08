from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_db
from viewer.adapter.outbound.pg.signup_pg_repository import SignupPgRepository
from viewer.app.ports.input.signup_use_case import SignupUseCase
from viewer.app.ports.output.signup_repository import SignupRepository
from viewer.app.use_cases.signup_interactor import SignupInteractor


def get_signup_use_case(db: AsyncSession = Depends(get_viewer_db)) -> SignupUseCase:
    repository: SignupRepository = SignupPgRepository(session=db)
    return SignupInteractor(repository=repository)
