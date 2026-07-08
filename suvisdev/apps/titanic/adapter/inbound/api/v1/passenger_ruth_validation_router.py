from fastapi import APIRouter, Depends

from titanic.adapter.inbound.api.schemas.passenger_ruth_validation_schema import (
    RuthValidationSchema,
)
from titanic.app.dtos.passenger_ruth_validation_dto import RuthValidationResponse
from titanic.app.ports.input.passenger_ruth_validation_use_case import RuthValidationUseCase
from titanic.dependencies.passenger_ruth_validation_provider import get_ruth_validation_use_case

ruth_validation_router = APIRouter(prefix="/ruth", tags=["ruth"])


@ruth_validation_router.get("/myself")
async def introduce_myself(
    ruth: RuthValidationUseCase = Depends(get_ruth_validation_use_case),
) -> RuthValidationResponse:
    return await ruth.introduce_myself(
        RuthValidationSchema(
            id=11,
            name="루스 검증 주인공"
        )
    )
