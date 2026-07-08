from fastapi import APIRouter, Depends

from titanic.adapter.inbound.api.schemas.crew_andrews_architect_schema import AndrewsArchitectSchema
from titanic.app.dtos.crew_andrews_architect_dto import AndrewsArchitectResponse
from titanic.app.ports.input.crew_andrews_architect_use_case import AndrewsArchitectUseCase
from titanic.dependencies.crew_andrews_architect_provider import get_andrews_architect_use_case

andrews_architect_router = APIRouter(prefix="/andrews", tags=["andrews"])

@andrews_architect_router.get("/myself")
async def introduce_myself(
    andrews: AndrewsArchitectUseCase = Depends(get_andrews_architect_use_case),
) -> AndrewsArchitectResponse:
    return await andrews.introduce_myself(
        AndrewsArchitectSchema(
            id=1,
            name="토마스 앤드류스 (Thomas Andrews)"
        )
    )
