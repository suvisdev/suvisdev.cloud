"""리뷰 감정분석 DI (백그라운드 태스크·CLI 배치·스케줄러용).

review_spoiler_provider와 같은 이유로 세션 팩토리를 직접 주입한다.
"""

from __future__ import annotations

from pathlib import Path

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository
from mova.app.use_cases.review_sentiment_backfill_interactor import (
    ReviewSentimentBackfillInteractor,
)
from ontology.app.ports.output.sentiment_analysis_port import SentimentAnalysisPort


def _make_echo_adapter() -> SentimentAnalysisPort:
    # ontology 어댑터는 lazy import — torch 로드가 무거워 GPU 경로에서만 당긴다.
    from ontology.adapter.outbound.resource_adapters.echo_sentiment.echo_sentiment_adapter import (
        EchoSentimentAdapter,
    )

    adapter_dir = (
        Path(__file__).resolve().parents[2] / "ontology" / "runs" / "echo_sentiment" / "adapter"
    )
    return EchoSentimentAdapter(adapter_dir=adapter_dir)


def get_review_sentiment_backfill_use_case() -> ReviewSentimentBackfillInteractor:
    return ReviewSentimentBackfillInteractor(
        session_factory=get_mova_session_factory(),
        reviews_repository=ReviewsPgRepository,
        make_analyzer=_make_echo_adapter,
    )
