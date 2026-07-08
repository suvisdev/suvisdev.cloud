from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from titanic.app.dtos.passenger_cal_tester_dto import CalTesterQuery, CalTesterResponse
from titanic.app.ports.output.passenger_cal_tester_port import CalTesterPort

logger = logging.getLogger(__name__)


class CalTesterRepository(CalTesterPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def introduce_myself(self, query: CalTesterQuery) -> CalTesterResponse:
        logger.info(f"[CalTesterRepository] introduce_myself 진입 | request_data={query}")
        response = CalTesterResponse(id=query.id * 10000, name=query.name + "가 레포지토리에 다녀옴")
        return response
