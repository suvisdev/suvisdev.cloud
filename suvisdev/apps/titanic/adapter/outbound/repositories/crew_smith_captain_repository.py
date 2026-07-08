from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from titanic.app.dtos.crew_smith_captain_dto import (
    SmithCaptainChatCommand,
    SmithCaptainQuery,
    SmithCaptainResponse,
    SmithChatResponse,
)
from titanic.app.ports.output.crew_smith_captain_port import SmithCaptainPort

logger = logging.getLogger(__name__)


class SmithCaptainRepository(SmithCaptainPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def chat(self, command: SmithCaptainChatCommand) -> SmithChatResponse:
        logger.info(f"[SmithCaptainRepository] chat | messages={len(command.messages)}개")
        last = command.messages[-1].content if command.messages else ""
        return SmithChatResponse(reply=f"(임시 응답) 질문을 받았습니다: {last}")


    async def introduce_myself(self, query: SmithCaptainQuery) -> SmithCaptainResponse:
        logger.info(f"[SmithCaptainRepository] introduce_myself 진입 | request_data={query}")
        return SmithCaptainResponse(id=query.id * 10000, name=query.name + "가 레포지토리에 다녀옴")
    
