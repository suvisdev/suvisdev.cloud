from fastapi import APIRouter, Depends

from execsuite.adapter.inbound.api.schemas.piper_dunn_coo_schema import DunnCooSchema
from execsuite.app.dtos.piper_dunn_coo_dto import DunnCooResponse
from execsuite.app.ports.input.piper_dunn_coo_use_case import DunnCooUseCase
from execsuite.dependencies.piper_dunn_coo_provider import get_dunn_coo_use_case

dunn_coo_router = APIRouter(prefix="/dunn", tags=["dunn"])


@dunn_coo_router.get("/myself")
async def introduce_myself(
    dunn: DunnCooUseCase = Depends(get_dunn_coo_use_case),
) -> DunnCooResponse:
    return await dunn.introduce_myself(DunnCooSchema(id=4, name="도널드 던 주인공"))
