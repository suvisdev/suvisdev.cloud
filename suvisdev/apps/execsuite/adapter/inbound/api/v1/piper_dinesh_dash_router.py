from fastapi import APIRouter, Depends

from execsuite.adapter.inbound.api.schemas.piper_dinesh_dash_schema import DineshDashSchema
from execsuite.app.dtos.piper_dinesh_dash_dto import DineshDashResponse
from execsuite.app.ports.input.piper_dinesh_dash_use_case import DineshDashUseCase
from execsuite.dependencies.piper_dinesh_dash_provider import get_dinesh_dash_use_case

dinesh_dash_router = APIRouter(prefix="/dinesh", tags=["dinesh"])


@dinesh_dash_router.get("/myself")
async def introduce_myself(
    dinesh: DineshDashUseCase = Depends(get_dinesh_dash_use_case),
) -> DineshDashResponse:
    return await dinesh.introduce_myself(
        DineshDashSchema(
            id=3,
            name="디네시 추그타이 주인공"
        )
    )
