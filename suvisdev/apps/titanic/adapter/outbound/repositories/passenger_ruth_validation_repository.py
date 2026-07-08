from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from titanic.app.dtos.passenger_ruth_validation_dto import (
    RuthValidationQuery,
    RuthValidationResponse,
)
from titanic.app.ports.output.passenger_ruth_validation_port import (
    RuthValidationPort,
)

logger = logging.getLogger(__name__)


class RuthValidationRepository(RuthValidationPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def introduce_myself(self, query: RuthValidationQuery) -> RuthValidationResponse:
        logger.info(f"[RuthValidationRepository] introduce_myself 진입 | request_data={query}")
        response = RuthValidationResponse(id=query.id * 10000, name=query.name + "가 레포지토리에 다녀옴")
        return response
