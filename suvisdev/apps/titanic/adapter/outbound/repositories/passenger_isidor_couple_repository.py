from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from titanic.app.dtos.passenger_isidor_couple_dto import IsidorCoupleQuery, IsidorCoupleResponse
from titanic.app.ports.output.passenger_isidor_couple_port import (
    IsidorCouplePort,
)

logger = logging.getLogger(__name__)


class IsidorCoupleRepository(IsidorCouplePort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def introduce_myself(self, query: IsidorCoupleQuery) -> IsidorCoupleResponse:
        logger.info(f"[IsidorCoupleRepository] introduce_myself 진입 | request_data={query}")
        response = IsidorCoupleResponse(id=query.id * 10000, name=query.name + "가 레포지토리에 다녀옴")
        return response
