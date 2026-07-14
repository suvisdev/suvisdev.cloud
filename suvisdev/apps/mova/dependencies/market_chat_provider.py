"""채팅 DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.llm.exaone_recommendation_adapter import (
    ExaoneRecommendationAdapter,
)
from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository
from mova.adapter.outbound.pg.user_preference_pg_repository import (
    UserPreferencePgRepository,
)
from mova.app.ports.input.market_chat_use_case import ChatUseCase
from mova.app.ports.output.llm_output_port import RecommendationPort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.user_preference_query_port import UserPreferenceQueryPort
from mova.app.use_cases.market_chat_interactor import ChatInteractor
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.dependencies.hub_rag_provider import get_hub_rag_use_case


def get_chat_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> ChatRepositoryPort:
    return ChatPgRepository(session=db)


def get_recommendation_port() -> RecommendationPort:
    return ExaoneRecommendationAdapter()


def get_user_preference_port(
    db: AsyncSession = Depends(get_mova_db),
) -> UserPreferenceQueryPort:
    return UserPreferencePgRepository(session=db)


def get_chat_use_case(
    repository: ChatRepositoryPort = Depends(get_chat_repository),
    recommender: RecommendationPort = Depends(get_recommendation_port),
    preferences: UserPreferenceQueryPort = Depends(get_user_preference_port),
    hub_rag: HubRagUseCase = Depends(get_hub_rag_use_case),
) -> ChatUseCase:
    return ChatInteractor(
        repository=repository,
        recommender=recommender,
        preferences=preferences,
        hub_rag=hub_rag,
    )


get_market_chat_use_case = get_chat_use_case
