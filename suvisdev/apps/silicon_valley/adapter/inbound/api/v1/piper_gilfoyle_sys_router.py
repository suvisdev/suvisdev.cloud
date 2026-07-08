from fastapi import APIRouter, Depends

from silicon_valley.adapter.inbound.api.schemas.piper_gilfoyle_sys_schema import GilfoyleSysSchema
from silicon_valley.app.dtos.piper_gilfoyle_sys_dto import GilfoyleSysResponse
from silicon_valley.app.ports.input.piper_gilfoyle_sys_use_case import GilfoyleSysUseCase
from silicon_valley.dependencies.piper_gilfoyle_sys_provider import get_gilfoyle_sys_use_case

gilfoyle_sys_router = APIRouter(prefix="/gilfoyle", tags=["gilfoyle"])


@gilfoyle_sys_router.get("/myself")
async def introduce_myself(
    gilfoyle: GilfoyleSysUseCase = Depends(get_gilfoyle_sys_use_case),
) -> GilfoyleSysResponse:
    return await gilfoyle.introduce_myself(
        GilfoyleSysSchema(
            id=2,
            name="버트람 길포일 주인공"
        )
    )
