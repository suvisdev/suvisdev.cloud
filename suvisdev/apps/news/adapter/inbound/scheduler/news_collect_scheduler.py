"""뉴스 수집 스케줄러 — lifespan 백그라운드 루프 (기본 30분 주기).

노트북에서만 켠다(`ENABLE_NEWS_SCHEDULER=true`). 집컴 예비 서버까지 돌면 같은 기사를 두 번 모으고
검색 API 하루 한도(25,000회)를 두 배로 쓴다. 기본값은 꺼짐 — 머지만으로는 아무것도 수집하지 않는다.
"""

from __future__ import annotations

import asyncio
import logging
import os

from news.dependencies.news_provider import (
    run_collect_once,
    run_digest_once,
    run_hot_once,
    run_summarize_once,
)

logger = logging.getLogger(__name__)

NEWS_COLLECT_INTERVAL_SECONDS = max(300, int(os.getenv("NEWS_COLLECT_INTERVAL_SECONDS", "1800")))
# 수집 뒤 한국어 제목·요약을 몇 건까지 할지. 노트북 EXAONE 7.8B 글당 약 3초 → 80건이면 4분 남짓(11-05 실측 기준).
# 30분 주기면 하루 3,840건까지 — 하루 수집량(약 1,000건)과 첫 적재분을 넉넉히 따라간다. 0 이면 요약하지 않는다.
NEWS_SUMMARY_BATCH = max(0, int(os.getenv("NEWS_SUMMARY_BATCH", "80")))


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
        try:
            hot = await run_hot_once()  # 요약보다 먼저 — 새 화제 글이 이번 주기에 요약되게
            logger.info("[news] 화제 수치 | %s · 오류 %d", hot.fetched, len(hot.errors))
            for err in hot.errors:
                logger.warning("[news] %s", err)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[news] 화제 수치 갱신 실패 — 다음 주기에 다시 시도")
        if NEWS_SUMMARY_BATCH:
            try:
                summary = await run_summarize_once(NEWS_SUMMARY_BATCH)
                logger.info(
                    "[news] 한국어 요약 | 완료 %d · 실패 %d · 모델 응답 없음 %s · %s",
                    summary.done,
                    summary.failed,
                    summary.unavailable,
                    summary.model,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[news] 요약 주기 실패 — 다음 주기에 다시 시도")
        try:  # 요약 뒤라 GPU 가 겹치지 않고, 노트북이 7시에 꺼져 있었으면 켜진 뒤 첫 주기에 보낸다
            digest = await run_digest_once()
            if digest is not None and digest.status not in ("not_due", "skipped"):
                logger.info(
                    "[news] 아침 메일 | %s · 후보 %d · 기술 %d · 보냄 %d",
                    digest.status,
                    digest.candidates,
                    digest.tech,
                    digest.sent,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[news] 아침 메일 실패 — 다음 주기에 다시 시도")
        await asyncio.sleep(NEWS_COLLECT_INTERVAL_SECONDS)
