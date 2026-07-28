from fastapi import APIRouter, Depends

from execsuite.adapter.inbound.api.schemas.piper_hendricks_ceo_schema import HendricksCeoSchema
from execsuite.app.dtos.piper_hendricks_ceo_dto import HendricksCeoResponse
from execsuite.app.ports.input.piper_hendricks_ceo_use_case import HendricksCeoUseCase
from execsuite.dependencies.piper_hendricks_ceo_provider import get_hendricks_ceo_use_case

hendricks_ceo_router = APIRouter(prefix="/hendricks", tags=["hendricks"])


@hendricks_ceo_router.get("/myself")
async def introduce_myself(
    hendricks: HendricksCeoUseCase = Depends(get_hendricks_ceo_use_case),
) -> HendricksCeoResponse:
    return await hendricks.introduce_myself(
        HendricksCeoSchema(
            id=1,
            name="리처드 헨드릭스 주인공"
        )
    )
