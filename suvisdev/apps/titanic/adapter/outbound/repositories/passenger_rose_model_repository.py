from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from titanic.adapter.outbound.orm.passenger_jack_trainer_orm import JackTrainerOrm
from titanic.adapter.outbound.orm.passenger_rose_model_orm import RoseModelOrm
from titanic.app.dtos.passenger_rose_model_dto import (
    RoseModelFeatureRow,
    RoseModelQuery,
    RoseModelResponse,
)
from titanic.app.ports.output.passenger_rose_model_port import RoseModelPort

logger = logging.getLogger(__name__)


class RoseModelRepository(RoseModelPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def introduce_myself(self, query: RoseModelQuery) -> RoseModelResponse:
        logger.info(f"[RoseModelRepository] introduce_myself 진입 | request_data={query}")
        response = RoseModelResponse(id=query.id * 10000, name=query.name + "가 레포지토리에 다녀옴")
        return response

    async def list_training_rows(self) -> list[RoseModelFeatureRow]:
        stmt = select(JackTrainerOrm, RoseModelOrm).join(
            RoseModelOrm, RoseModelOrm.passenger_id == JackTrainerOrm.passenger_id,
        )
        result = await self._session.execute(stmt)
        return [
            RoseModelFeatureRow(
                pclass=booking.pclass,
                sex=passenger.gender,
                age=passenger.age,
                sib_sp=passenger.sib_sp,
                parch=passenger.parch,
                fare=booking.fare,
                embarked=booking.embarked,
                survived=passenger.survived,
            )
            for passenger, booking in result.all()
        ]
