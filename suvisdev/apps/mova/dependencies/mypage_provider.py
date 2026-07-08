from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.mypage_pg_repository import MypagePgRepository
from mova.app.ports.input.mypage_use_case import MypageUseCase
from mova.app.use_cases.mypage_interactor import MypageInteractor


def get_mypage_use_case(
    db: AsyncSession = Depends(get_mova_db),
) -> MypageUseCase:
    return MypageInteractor(repository=MypagePgRepository(session=db))
