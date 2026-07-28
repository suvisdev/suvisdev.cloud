from fastapi import APIRouter, Depends

from execsuite.adapter.inbound.api.schemas.piper_bighetti_hr_schema import BighettiHrSchema
from execsuite.app.dtos.piper_bighetti_hr_dto import BighettiHrResponse
from execsuite.app.ports.input.piper_bighetti_hr_use_case import BighettiHrUseCase
from execsuite.dependencies.piper_bighetti_hr_provider import get_bighetti_hr_use_case

bighetti_hr_router = APIRouter(prefix="/bighetti", tags=["bighetti"])


@bighetti_hr_router.get("/myself")
async def introduce_myself(
    bighetti: BighettiHrUseCase = Depends(get_bighetti_hr_use_case),
) -> BighettiHrResponse:
    return await bighetti.introduce_myself(
        BighettiHrSchema(
            id=5,
            name="넬슨 빅헤티 주인공"
        )
    )
