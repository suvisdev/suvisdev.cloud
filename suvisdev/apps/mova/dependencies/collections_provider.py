"""컬렉션 DI — Repository + UseCase 조립."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.market_collections_pg_repository import CollectionsPgRepository
from mova.app.ports.input.collections_use_case import (
    CreateCollectionUseCase,
    GetCollectionUseCase,
    ListCollectionMoviesUseCase,
    ListCollectionsUseCase,
)
from mova.app.ports.output.market_collections_repository import CollectionRepositoryPort
from mova.app.use_cases.collections_interactor import CollectionsInteractor


def get_collections_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> CollectionRepositoryPort:
    return CollectionsPgRepository(session=db)


def get_collections_interactor(
    repository: CollectionRepositoryPort = Depends(get_collections_repository),
) -> CollectionsInteractor:
    return CollectionsInteractor(repository=repository)


def get_create_collection_use_case(
    interactor: CollectionsInteractor = Depends(get_collections_interactor),
) -> CreateCollectionUseCase:
    return interactor


def get_list_collections_use_case(
    interactor: CollectionsInteractor = Depends(get_collections_interactor),
) -> ListCollectionsUseCase:
    return interactor


def get_get_collection_use_case(
    interactor: CollectionsInteractor = Depends(get_collections_interactor),
) -> GetCollectionUseCase:
    return interactor


def get_list_collection_movies_use_case(
    interactor: CollectionsInteractor = Depends(get_collections_interactor),
) -> ListCollectionMoviesUseCase:
    return interactor
