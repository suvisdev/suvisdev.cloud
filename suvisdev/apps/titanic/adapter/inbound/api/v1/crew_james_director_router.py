import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from titanic.adapter.inbound.api.schemas.crew_james_director_schema import JamesIntroduceSchema
from titanic.app.dtos.crew_james_director_dto import JamesIntroduceResponse, JamesResponse
from titanic.app.ports.input.crew_james_director_use_case import JamesUseCase
from titanic.dependencies.crew_james_director_provider import get_james_director_use_case

james_director_router = APIRouter(prefix="/james", tags=["james"])
logger = logging.getLogger(__name__)


@james_director_router.get("/myself")
async def introduce_myself(
    james: JamesUseCase = Depends(get_james_director_use_case),
) -> JamesIntroduceResponse:
    return await james.introduce_myself(
        JamesIntroduceSchema(
            id=12,
            name="제임스 카메론 (James Cameron)",
        )
    )


@james_director_router.post("/upload")
async def receive_uploaded_records(
    file: UploadFile = File(...),
    james: JamesUseCase = Depends(get_james_director_use_case),
) -> JamesResponse:
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    try:
        return await james.receive_uploaded_records(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
