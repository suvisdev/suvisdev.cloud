from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from dispatch.adapter.inbound.api.schemas.adress_schema import (
    AdressIntroduceSchema,
    AdressSearchItemSchema,
)
from dispatch.app.dtos.adress_dto import AdressIntroduceResponse, AdressResponse
from dispatch.app.ports.input.adress_use_case import AdressUseCase
from dispatch.dependencies.adress_provider import get_adress_use_case

adress_router = APIRouter(prefix="/adress", tags=["dispatch-adress"])


@adress_router.get("/myself")
async def introduce_myself(
    use_case: AdressUseCase = Depends(get_adress_use_case),
) -> AdressIntroduceResponse:
    return await use_case.introduce_myself(AdressIntroduceSchema(id=2, name="주소록 관리"))


@adress_router.get("/search")
async def search_adress(
    q: str = Query(default="", min_length=1),
    use_case: AdressUseCase = Depends(get_adress_use_case),
) -> list[AdressSearchItemSchema]:
    results = await use_case.search(q)
    return [AdressSearchItemSchema(name=r.name, email=r.email) for r in results]


@adress_router.post("/upload")
async def receive_uploaded_records(
    file: UploadFile = File(...),
    use_case: AdressUseCase = Depends(get_adress_use_case),
) -> AdressResponse:
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    try:
        return await use_case.receive_uploaded_records(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
