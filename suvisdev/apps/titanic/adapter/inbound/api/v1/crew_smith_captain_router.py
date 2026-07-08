import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.params import Body

from titanic.adapter.inbound.api.schemas.crew_smith_captain_schema import (
    ChatSchema,
    SmithCaptainSchema,
)
from titanic.app.dtos.crew_smith_captain_dto import SmithCaptainResponse, SmithChatResponse
from titanic.app.ports.input.crew_smith_captain_use_case import SmithCaptainUseCase
from titanic.dependencies.crew_smith_captain_provider import get_smith_captain_use_case

logger = logging.getLogger(__name__)

smith_captain_router = APIRouter(prefix="/smith", tags=["smith"])


@smith_captain_router.post("/chat")
async def chat(
    schema: Annotated[ChatSchema, Body()],
    smith: SmithCaptainUseCase = Depends(get_smith_captain_use_case),
) -> SmithChatResponse:
    # suvis 안의 smith-captain/page.tsx 에서 /api/titanic/smith/chat 이 URL로
    # 키 값이 messages인 Body()로 보낸 내용을 로그로 출력하는 코드
    logger.info(f"[SmithCaptainRouter] messages | content={schema.messages[:50]}...")
    return await smith.chat(schema)


@smith_captain_router.get("/myself")
async def introduce_myself(
    smith: SmithCaptainUseCase = Depends(get_smith_captain_use_case),
) -> SmithCaptainResponse:
    return await smith.introduce_myself(
        SmithCaptainSchema(
            id=4,
            name="스미스 캡틴 주인공"
        )
    )
