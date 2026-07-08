"""컬렉션 라우터 — GET /mova/collections/{slug}, GET /mova/collections/{slug}/movies."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.market_collections_schema import (
    CollectionCreateSchema,
    CollectionDetailSchema,
    CollectionListSchema,
    CollectionMoviesSchema,
)
from mova.app.dtos.market_collections_dto import CollectionCreateCommand
from mova.app.ports.input.collections_use_case import (
    CreateCollectionUseCase,
    GetCollectionUseCase,
    ListCollectionMoviesUseCase,
    ListCollectionsUseCase,
)
from mova.dependencies.collections_provider import (
    get_create_collection_use_case,
    get_get_collection_use_case,
    get_list_collection_movies_use_case,
    get_list_collections_use_case,
)

collections_router = APIRouter(prefix="/collections", tags=["mova-collections"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@collections_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="큐레이터 (Curator)")


@collections_router.post("", response_model=CollectionDetailSchema, status_code=201)
async def create_collection(
    body: CollectionCreateSchema,
    collections: CreateCollectionUseCase = Depends(get_create_collection_use_case),
) -> CollectionDetailSchema:
    """컬렉션 생성."""
    try:
        command = CollectionCreateCommand.from_payload(
            slug=body.slug,
            name=body.name,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        dto = await collections.create_collection(command)
    except ValueError as exc:
        detail = str(exc)
        if "already exists" in detail:
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=422, detail=detail) from exc
    return dto.to_schema()


@collections_router.get("", response_model=CollectionListSchema)
async def list_collections(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    collections: ListCollectionsUseCase = Depends(get_list_collections_use_case),
) -> CollectionListSchema:
    """컬렉션 목록 조회."""
    dto = await collections.list_collections(limit=limit, offset=offset)
    return dto.to_schema()


@collections_router.get("/{slug}", response_model=CollectionDetailSchema)
async def get_collection(
    slug: str,
    collections: GetCollectionUseCase = Depends(get_get_collection_use_case),
) -> CollectionDetailSchema:
    """컬렉션 상세 — 소속 영화 수 포함."""
    dto = await collections.get_collection(slug)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Collection '{slug}' not found")
    return dto.to_schema()


@collections_router.get("/{slug}/movies", response_model=CollectionMoviesSchema)
async def list_collection_movies(
    slug: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    collections: ListCollectionMoviesUseCase = Depends(get_list_collection_movies_use_case),
) -> CollectionMoviesSchema:
    """컬렉션에 속한 영화 목록 (movies.collection_id FK 기준)."""
    dto = await collections.list_collection_movies(slug, limit=limit, offset=offset)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Collection '{slug}' not found")
    return dto.to_schema()
