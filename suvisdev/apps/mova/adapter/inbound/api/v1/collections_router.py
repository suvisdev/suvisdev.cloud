"""컬렉션 라우터 — GET /mova/collections/{slug}, GET /mova/collections/{slug}/movies."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from shared.security.require_admin import AdminPrincipal, require_admin

from mova.adapter.inbound.api.schemas.market_collections_schema import (
    CollectionAssignResultSchema,
    CollectionCreateSchema,
    CollectionDetailSchema,
    CollectionListSchema,
    CollectionMoviesMutationRequest,
    CollectionMoviesSchema,
)
from mova.app.dtos.market_collections_dto import CollectionCreateCommand
from mova.app.ports.input.collections_use_case import (
    AssignMoviesUseCase,
    CreateCollectionUseCase,
    GetCollectionUseCase,
    ListCollectionMoviesUseCase,
    ListCollectionsUseCase,
    UnassignMoviesUseCase,
)
from mova.dependencies.collections_provider import (
    get_assign_movies_use_case,
    get_create_collection_use_case,
    get_get_collection_use_case,
    get_list_collection_movies_use_case,
    get_list_collections_use_case,
    get_unassign_movies_use_case,
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


@collections_router.patch("/{slug}/movies", response_model=CollectionAssignResultSchema)
async def assign_movies_to_collection(
    slug: str,
    body: CollectionMoviesMutationRequest,
    _: AdminPrincipal = Depends(require_admin),
    collections: AssignMoviesUseCase = Depends(get_assign_movies_use_case),
) -> CollectionAssignResultSchema:
    """영화를 이 컬렉션으로 배정 — 어드민 전용.

    one-to-many(`movies.collection_id` FK) 구조라 다른 컬렉션에 이미 속한
    영화도 이 컬렉션으로 이동한다(덮어쓰기). 관측성 위해
    `moved_from_other_collection` 카운트를 응답에 노출. DB에 없는 movie_id는
    `skipped_ids`로 분리 반환(부분 성공, 404 안 냄).
    """
    dto = await collections.assign_movies(slug, body.movie_ids)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Collection '{slug}' not found")
    return dto.to_schema()


@collections_router.delete("/{slug}/movies", response_model=CollectionAssignResultSchema)
async def unassign_movies_from_collection(
    slug: str,
    body: CollectionMoviesMutationRequest,
    _: AdminPrincipal = Depends(require_admin),
    collections: UnassignMoviesUseCase = Depends(get_unassign_movies_use_case),
) -> CollectionAssignResultSchema:
    """영화의 이 컬렉션 배정 해제 — 어드민 전용, idempotent.

    이 컬렉션에 속하지 않은 movie_id(다른 컬렉션 소속 또는 어디에도 없음)는
    `skipped_ids`로 담아 조용히 반환. 실제 NULL 처리된 영화 수는 `affected`.
    """
    dto = await collections.unassign_movies(slug, body.movie_ids)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Collection '{slug}' not found")
    return dto.to_schema()
