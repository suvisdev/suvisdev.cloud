from fastapi import APIRouter, Depends

from titanic.adapter.inbound.api.schemas.crew_hartley_violin_schema import HartleyViolinSchema
from titanic.app.dtos.crew_hartley_violin_dto import HartleyViolinResponse
from titanic.app.ports.input.crew_hartley_violin_use_case import HartleyViolinUseCase
from titanic.dependencies.crew_hartley_violin_provider import get_hartley_violin_use_case

hartley_violin_router = APIRouter(prefix="/hartley", tags=["hartley"])


@hartley_violin_router.get("/myself")
async def introduce_myself(
    hartley: HartleyViolinUseCase = Depends(get_hartley_violin_use_case),
) -> HartleyViolinResponse:
    return await hartley.introduce_myself(
        HartleyViolinSchema(
            id=2,
            name="하트리 바이올린 주인공"
        )
    )
