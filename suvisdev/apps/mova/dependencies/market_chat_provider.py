"""채팅 DI."""

import os

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.outbound.http.kakao_local_adapter import KakaoLocalTheaterAdapter
from mova.adapter.outbound.http.kofic_box_office_adapter import KoficBoxOfficeAdapter
from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter
from mova.adapter.outbound.http.tmdb_review_adapter import TmdbReviewAdapter
from mova.adapter.outbound.llm.fallback_recommendation_adapter import (
    FallbackRecommendationAdapter,
)
from mova.adapter.outbound.llm.gemini_recommendation_adapter import (
    GeminiRecommendationAdapter,
)
from mova.adapter.outbound.llm.lora_recommendation_adapter import (
    LoraRecommendationAdapter,
)
from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
from mova.adapter.outbound.pg.platform_user_taste_vectors_pg_repository import (
    UserTasteVectorsPgRepository,
)
from mova.adapter.outbound.pg.review_aggregation_pg_repository import (
    ReviewAggregationPgRepository,
)
from mova.adapter.outbound.pg.user_preference_pg_repository import (
    UserPreferencePgRepository,
)
from mova.app.ports.input.market_chat_use_case import ChatUseCase
from mova.app.ports.output.llm_output_port import RecommendationPort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.market_conversations_repository import ConversationsRepository
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.platform_user_taste_vector_repository import (
    UserTasteVectorRepositoryPort,
)
from mova.app.ports.output.user_preference_query_port import UserPreferenceQueryPort
from mova.app.use_cases.market_chat_booking_interactor import BookingAssistService
from mova.app.use_cases.market_chat_evaluation_interactor import MovieEvaluationService
from mova.app.use_cases.market_chat_interactor import ChatInteractor
from mova.dependencies.market_conversations_provider import get_conversations_repository
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase
from ontology.app.ports.output.intent_classifier_port import IntentClassifierPort
from ontology.dependencies.hub_rag_provider import get_hub_rag_use_case
from ontology.dependencies.semantic_router_provider import (
    get_intent_classifier,
    get_semantic_mycroft_use_case,
)


def get_chat_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> ChatRepositoryPort:
    return ChatPgRepository(session=db)


def get_recommendation_port() -> RecommendationPort:
    backend = os.getenv("RECOMMENDATION_BACKEND", "lora")
    if backend == "gemini":
        return GeminiRecommendationAdapter()
    # lora 실패(서킷 오픈 포함) 시 Gemini로 자동 폴백. 서킷 쿨다운(60초)이
    # 지나면 primary(LoRA)를 다시 시도하므로 서버 복구 시 자동 복귀한다.
    return FallbackRecommendationAdapter(
        primary=LoraRecommendationAdapter(),
        fallback=GeminiRecommendationAdapter(),
    )


def get_user_preference_port(
    db: AsyncSession = Depends(get_mova_db),
) -> UserPreferenceQueryPort:
    return UserPreferencePgRepository(session=db)


def get_movies_repository_for_chat(
    db: AsyncSession = Depends(get_mova_db),
) -> MoviesRepositoryPort:
    return MoviesPgRepository(session=db)


def get_user_taste_vector_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> UserTasteVectorRepositoryPort:
    return UserTasteVectorsPgRepository(session=db)


def get_evaluation_service(
    db: AsyncSession = Depends(get_mova_db),
    general: MycroftUseCase = Depends(get_semantic_mycroft_use_case),
) -> MovieEvaluationService:
    keymaker = get_keymaker()
    # TMDB 키 미설정이면 외부 리뷰만 생략 — 평가 트랙 자체는 자체 리뷰로 동작.
    external = (
        TmdbReviewAdapter(TmdbAdapter(keymaker.tmdb_api_key)) if keymaker.tmdb_api_key else None
    )
    return MovieEvaluationService(
        repository=ChatPgRepository(session=db),
        movies=MoviesPgRepository(session=db),
        reviews=ReviewAggregationPgRepository(session=db),
        general=general,
        external_reviews=external,
    )


def get_booking_service(
    db: AsyncSession = Depends(get_mova_db),
) -> BookingAssistService:
    keymaker = get_keymaker()
    return BookingAssistService(
        repository=ChatPgRepository(session=db),
        movies=MoviesPgRepository(session=db),
        box_office=KoficBoxOfficeAdapter(keymaker.kofic_api_key),
        # gildle 지오코딩과 같은 키 재사용(mova 자체 어댑터 — 스포크 간 import 금지).
        theaters=KakaoLocalTheaterAdapter(os.getenv("KAKAO_API_KEY") or ""),
    )


def get_chat_use_case(
    repository: ChatRepositoryPort = Depends(get_chat_repository),
    recommender: RecommendationPort = Depends(get_recommendation_port),
    preferences: UserPreferenceQueryPort = Depends(get_user_preference_port),
    hub_rag: HubRagUseCase = Depends(get_hub_rag_use_case),
    classifier: IntentClassifierPort = Depends(get_intent_classifier),
    general: MycroftUseCase = Depends(get_semantic_mycroft_use_case),
    conversations: ConversationsRepository = Depends(get_conversations_repository),
    movies: MoviesRepositoryPort = Depends(get_movies_repository_for_chat),
    taste_vectors: UserTasteVectorRepositoryPort = Depends(get_user_taste_vector_repository),
    evaluation: MovieEvaluationService = Depends(get_evaluation_service),
    booking: BookingAssistService = Depends(get_booking_service),
) -> ChatUseCase:
    return ChatInteractor(
        repository=repository,
        recommender=recommender,
        preferences=preferences,
        hub_rag=hub_rag,
        classifier=classifier,
        general=general,
        conversations=conversations,
        movies=movies,
        taste_vectors=taste_vectors,
        evaluation=evaluation,
        booking=booking,
    )


get_market_chat_use_case = get_chat_use_case
