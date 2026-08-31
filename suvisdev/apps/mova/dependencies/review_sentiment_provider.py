"""리뷰 감정분석 DI (백그라운드 태스크·CLI 배치용).

review_spoiler_provider와 같은 이유로 세션 팩토리를 직접 주입한다.
"""

from __future__ import annotations

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from mova.app.use_cases.review_sentiment_backfill_interactor import (
    ReviewSentimentBackfillInteractor,
)


def get_review_sentiment_backfill_use_case() -> ReviewSentimentBackfillInteractor:
    return ReviewSentimentBackfillInteractor(session_factory=get_mova_session_factory())
