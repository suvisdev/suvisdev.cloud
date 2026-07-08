from fastapi import APIRouter, Depends

from titanic.adapter.inbound.api.schemas.crew_lowe_boat_schema import LoweBoatSchema
from titanic.app.dtos.crew_lowe_boat_dto import LoweBoatResponse
from titanic.app.ports.input.crew_lowe_boat_use_case import LoweBoatUseCase
from titanic.dependencies.crew_lowe_boat_provider import get_lowe_boat_use_case

lowe_boat_router = APIRouter(prefix="/lowe", tags=["lowe"])


@lowe_boat_router.get("/myself")
async def introduce_myself(
    lowe: LoweBoatUseCase = Depends(get_lowe_boat_use_case),
) -> LoweBoatResponse:
    return await lowe.introduce_myself(
        LoweBoatSchema(
            id=3,
            name="로우 보트 주인공"
        )
    )
