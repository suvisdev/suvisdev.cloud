from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from titanic.app.dtos.crew_andrews_architect_dto import (
    AndrewsArchitectQuery,
    AndrewsArchitectResponse,
)
from titanic.app.ports.output.crew_andrews_architect_port import AndrewsArchitectPort

logger = logging.getLogger(__name__)


class AndrewsArchitectRepository(AndrewsArchitectPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def introduce_myself(self, query: AndrewsArchitectQuery) -> AndrewsArchitectResponse:
        
        logger.info(f"[AndrewsArchitectRepository] introduce_myself 진입 | request_data={query}")

        response = AndrewsArchitectResponse(id=query.id * 10000, name=query.name + "가 레포지토리에 다녀옴")
        
        return response
