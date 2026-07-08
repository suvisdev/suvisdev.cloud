from fastapi import APIRouter, Depends

from titanic.adapter.inbound.api.schemas.passenger_isidor_couple_schema import IsidorCoupleSchema
from titanic.app.dtos.passenger_isidor_couple_dto import IsidorCoupleResponse
from titanic.app.ports.input.passenger_isidor_couple_use_case import IsidorCoupleUseCase
from titanic.dependencies.passenger_isidor_couple_provider import get_isidor_couple_use_case

isidor_couple_router = APIRouter(prefix="/isidor", tags=["isidor"])


@isidor_couple_router.get("/myself")
async def introduce_myself(
    isidor: IsidorCoupleUseCase = Depends(get_isidor_couple_use_case),
) -> IsidorCoupleResponse:
    return await isidor.introduce_myself(
        IsidorCoupleSchema(
            id=7,
            name="이시도르 커플 주인공"
        )
    )
