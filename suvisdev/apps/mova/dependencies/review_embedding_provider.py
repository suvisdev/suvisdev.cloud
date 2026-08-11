"""리뷰 임베딩 백필 DI.

BackgroundTasks에서 호출하는 인터랙터라 request-scoped 세션(`get_mova_db`)을
쓰지 않고 세션 팩토리를 직접 주입한다 — 응답 반환 후 도는 코드가 이미
close된 세션에 붙지 않게 하려는 목적. [[market_reviews_provider]]는 요청
경로용 인터랙터를 조립하고, 여기는 백그라운드 경로용을 조립한다.
"""

from __future__ import annotations

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from mova.app.use_cases.review_embedding_backfill_interactor import (
    ReviewEmbeddingBackfillInteractor,
)
from ontology.adapter.outbound.llm.gemini_embedding_adapter import GeminiEmbeddingAdapter


def get_review_embedding_backfill_use_case() -> ReviewEmbeddingBackfillInteractor:
    return ReviewEmbeddingBackfillInteractor(
        session_factory=get_mova_session_factory(),
        embedder=GeminiEmbeddingAdapter(),
    )
