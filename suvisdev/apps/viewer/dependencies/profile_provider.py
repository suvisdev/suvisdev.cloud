from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_db
from viewer.adapter.outbound.pg.profile_pg_repository import ProfilePgRepository
from viewer.app.ports.input.profile_use_case import ProfileUseCase
from viewer.app.ports.output.profile_repository import ProfileRepository
from viewer.app.use_cases.profile_interactor import ProfileInteractor


def get_profile_use_case(db: AsyncSession = Depends(get_viewer_db)) -> ProfileUseCase:
    repository: ProfileRepository = ProfilePgRepository(session=db)
    return ProfileInteractor(repository=repository)
