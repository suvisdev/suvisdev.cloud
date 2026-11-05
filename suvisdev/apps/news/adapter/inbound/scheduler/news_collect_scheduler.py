"""뉴스 수집 스케줄러 — lifespan 백그라운드 루프 (기본 30분 주기).

노트북에서만 켠다(`ENABLE_NEWS_SCHEDULER=true`). 집컴 예비 서버까지 돌면 같은 기사를 두 번 모으고
검색 API 하루 한도(25,000회)를 두 배로 쓴다. 기본값은 꺼짐 — 머지만으로는 아무것도 수집하지 않는다.
"""

from __future__ import annotations

import asyncio
import logging
import os

from news.dependencies.news_provider import run_collect_once

logger = logging.getLogger(__name__)

NEWS_COLLECT_INTERVAL_SECONDS = max(300, int(os.getenv("NEWS_COLLECT_INTERVAL_SECONDS", "1800")))


def news_scheduler_enabled() -> bool:
    return os.getenv("ENABLE_NEWS_SCHEDULER", "false").strip().lower() in ("true", "1", "yes")


async def run_news_collect_scheduler() -> None:
    while True:
        try:
            report = await run_collect_once()
            logger.info(
                "[news] 수집 완료 | 탭 %d · RSS %d · 받음 %d · 무관 %d · 새 기사 %d · 판정 %d %s · 오류 %d",
                report.topics,
                report.feeds,
                report.fetched,
                report.irrelevant,
                report.new_articles,
                report.judged,
                report.verdicts,
                len(report.errors),
            )
            for err in report.errors:
                logger.warning("[news] %s", err)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[news] 수집 주기 실패 — 다음 주기에 다시 시도")
        await asyncio.sleep(NEWS_COLLECT_INTERVAL_SECONDS)
