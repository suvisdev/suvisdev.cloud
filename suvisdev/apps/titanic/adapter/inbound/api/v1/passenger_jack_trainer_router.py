from typing import Any

from fastapi import APIRouter, Depends

from titanic.adapter.inbound.api.schemas.passenger_jack_trainer_schema import JackTrainerSchema
from titanic.app.dtos.passenger_jack_trainer_dto import JackTrainerResponse
from titanic.app.ports.input.passenger_jack_trainer_use_case import JackTrainerUseCase
from titanic.dependencies.passenger_jack_trainer_provider import get_jack_trainer_use_case

jack_trainer_router = APIRouter(prefix="/jack", tags=["jack"])


@jack_trainer_router.get("/myself")
async def introduce_myself(
    jack: JackTrainerUseCase = Depends(get_jack_trainer_use_case),
) -> JackTrainerResponse:
    return await jack.introduce_myself(
        JackTrainerSchema(
            id=8,
            name="잭 트레이너 주인공"
        )
    )


@jack_trainer_router.post("/train")
async def get_model_train() -> dict[str, Any]:
    return {"message": "훈련은 /smith/chat 을 통해 자동으로 실행됩니다."}
