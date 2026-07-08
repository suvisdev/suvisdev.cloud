from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from titanic.adapter.outbound.orm.passenger_jack_trainer_orm import JackTrainerOrm
from titanic.adapter.outbound.orm.passenger_rose_model_orm import RoseModelOrm
from titanic.app.dtos.crew_walter_roaster_dto import WalterQuery, WalterResponse
from titanic.app.ports.output.crew_walter_roaster_port import WalterPort

logger = logging.getLogger(__name__)


class WalterRepository(WalterPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_train_set(self) -> pd.DataFrame:
        ''' survived 컬럼이 있는 데이터 전체를 데이터프레임으로 반환하는 메소드'''
        stmt = (
            select(JackTrainerOrm, RoseModelOrm)
            .join(RoseModelOrm, RoseModelOrm.passenger_id == JackTrainerOrm.passenger_id)
            .where(JackTrainerOrm.survived != "")
        )
        result = await self._session.execute(stmt)
        return pd.DataFrame([
            {
                "passenger_id": p.passenger_id,
                "name": p.name,
                "gender": p.gender,
                "age": p.age,
                "sib_sp": p.sib_sp,
                "parch": p.parch,
                "survived": p.survived,
                "pclass": b.pclass,
                "ticket": b.ticket,
                "fare": b.fare,
                "cabin": b.cabin,
                "embarked": b.embarked,
            }
            for p, b in result.all()
        ])

    async def get_test_set(self) -> pd.DataFrame:
        ''' survived 컬럼이 없는 데이터 전체를 데이터프레임으로 반환하는 메소드 '''
        stmt = (
            select(JackTrainerOrm, RoseModelOrm)
            .join(RoseModelOrm, RoseModelOrm.passenger_id == JackTrainerOrm.passenger_id)
            .where(JackTrainerOrm.survived == "")
        )
        result = await self._session.execute(stmt)
        return pd.DataFrame([
            {
                "passenger_id": p.passenger_id,
                "name": p.name,
                "gender": p.gender,
                "age": p.age,
                "sib_sp": p.sib_sp,
                "parch": p.parch,
                "pclass": b.pclass,
                "ticket": b.ticket,
                "fare": b.fare,
                "cabin": b.cabin,
                "embarked": b.embarked,
            }
            for p, b in result.all()
        ])

    async def introduce_myself(self, query: WalterQuery) -> WalterResponse:
        logger.info(f"[WalterRepository] introduce_myself 진입 | request_data={query}")
        response = WalterResponse(id=query.id * 10000, name=query.name + "가 레포지토리에 다녀옴")
        return response
