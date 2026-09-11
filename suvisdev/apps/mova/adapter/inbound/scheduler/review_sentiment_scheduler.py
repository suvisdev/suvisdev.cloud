"""리뷰 감정분석 자동 스케줄러 — lifespan 백그라운드 루프 (24시간 주기).

sentiment_label IS NULL인 리뷰를 순회하며 Echo(EXAONE-3.5-2.4B + LoRA)로
감정분석 후 결과를 DB에 저장한다. 에디터 리뷰(rating=NULL)는 감정 기반
자동 별점도 함께 생성한다.

GPU가 없는 배포 환경에서는 첫 실행에서 모델 로드 실패 → 로그 후 루프 종료.
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

SENTIMENT_INTERVAL_SECONDS = 24 * 60 * 60  # 24시간
_BATCH_LIMIT = int(os.getenv("SENTIMENT_BATCH_LIMIT", "50"))


async def run_sentiment_once(limit: int = _BATCH_LIMIT) -> dict[str, int]:
    """미처리 리뷰 감정분석 1회 실행. 수동 스크립트와 공유 가능."""
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from mova.app.use_cases.review_sentiment_backfill_interactor import (
        ReviewSentimentBackfillInteractor,
    )

    factory = get_mova_session_factory()
    interactor = ReviewSentimentBackfillInteractor(session_factory=factory)
    return await interactor.analyze_missing(limit=limit)


async def run_sentiment_scheduler() -> None:
    """24시간 간격으로 미처리 리뷰 감정분석을 자동 실행한다.

    GPU가 없으면 첫 주기에서 전부 failed → 이후 주기에도 같은 결과이므로
    succeeded=0이 연속 2회면 루프를 종료한다.
    """
    consecutive_empty = 0
    while True:
        try:
            stats = await run_sentiment_once()
            logger.info(
                "[sentiment-scheduler] 주기 완료 — %s",
                ", ".join(f"{k}={v}" for k, v in stats.items()),
            )
            if stats.get("succeeded", 0) == 0 and stats.get("skipped", 0) == 0:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info(
                        "[sentiment-scheduler] 연속 %d회 처리 대상 없음, 루프 종료"
                        " (GPU 미탑재 환경이거나 전부 처리 완료)",
                        consecutive_empty,
                    )
                    return
            else:
                consecutive_empty = 0
        except Exception as e:
            logger.warning("[sentiment-scheduler] 주기 실행 실패: %s", e)
        await asyncio.sleep(SENTIMENT_INTERVAL_SECONDS)
