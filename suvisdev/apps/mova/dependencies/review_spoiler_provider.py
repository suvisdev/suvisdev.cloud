"""리뷰 스포일러 감지 DI (백그라운드 태스크용).

review_embedding_provider와 같은 이유로 세션 팩토리를 직접 주입한다.
"""

from __future__ import annotations

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from mova.adapter.outbound.llm.spoiler_detection import detect_spoiler_spans
from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository
from mova.app.use_cases.review_spoiler_backfill_interactor import (
    ReviewSpoilerBackfillInteractor,
)


def get_review_spoiler_backfill_use_case() -> ReviewSpoilerBackfillInteractor:
    return ReviewSpoilerBackfillInteractor(
        session_factory=get_mova_session_factory(),
        reviews_repository=ReviewsPgRepository,
        detect_spans=detect_spoiler_spans,
    )
