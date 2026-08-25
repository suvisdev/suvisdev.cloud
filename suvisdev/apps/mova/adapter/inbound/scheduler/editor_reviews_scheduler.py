"""에디터 리뷰 자동 생성 스케줄러 — lifespan 백그라운드 루프 (24시간 주기).

구글 뉴스 RSS(제목+요약만 — 기사 원문 미수집, GoogleNewsScraper와 동일한
저작권 원칙)에서 영화별 언론 반응을 모아 Gemini로 3~4문장 리뷰를 생성하고,
시스템 계정("Mova 에디터")으로 reviews에 저장한다. UNIQUE(user_id, movie_id)
덕에 영화당 1건 — 매 주기 "아직 에디터 리뷰가 없는" 영화만 새로 채워진다.

수동 실행은 scripts/generate_editor_reviews.py(이 모듈의 얇은 래퍼)로 동일
로직을 쓴다.
"""

from __future__ import annotations

import asyncio
import logging
import os
from urllib.parse import quote

logger = logging.getLogger(__name__)

EDITOR_USERNAME = "mova_editor"
EDITOR_NICKNAME = "Mova 에디터"
_FEED_URL = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
_GEMINI_SLEEP_SECONDS = 4.5  # 무료 티어 15req/min
EDITOR_REVIEWS_INTERVAL_SECONDS = 24 * 60 * 60  # 24시간
# 사용자 지정: 하루 10~20편 — 기본 15, env로 조절.
_DAILY_LIMIT = int(os.getenv("EDITOR_REVIEWS_DAILY_LIMIT", "15"))

REVIEW_PROMPT = """아래는 영화 "{title}"({year})에 대한 최근 뉴스 기사 제목·요약 목록입니다.
이를 바탕으로 영화 소개 리뷰를 한국어 3~4문장으로 작성하세요.

규칙:
- 언론의 평가·반응을 중립적으로 요약하는 어조 (과장 광고체 금지)
- 스포일러(결말·반전) 금지
- 기사에 없는 사실을 지어내지 말 것. 기사 내용이 영화와 무관하면 "SKIP"만 출력
- 출처·매체명·기자명 언급 금지, 순수 리뷰 문장만 출력

기사 목록:
{articles}
"""


def _fetch_news(title: str) -> list[str]:
    import feedparser
    from bs4 import BeautifulSoup

    feed = feedparser.parse(_FEED_URL.format(query=quote(f'"{title}" 영화')))
    rows: list[str] = []
    for e in feed.entries[:8]:
        summary = BeautifulSoup(getattr(e, "summary", ""), "html.parser").get_text(
            separator=" ", strip=True
        )
        rows.append(f"- {e.title}: {summary[:200]}")
    return rows


async def _ensure_editor_user() -> int:
    from sqlalchemy import select, text

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from viewer.adapter.outbound.orm.user_orm import User

    factory = get_mova_session_factory()
    async with factory() as session:
        editor_id = (
            await session.execute(select(User.id).where(User.username == EDITOR_USERNAME))
        ).scalar_one_or_none()
        if editor_id is not None:
            return int(editor_id)
        group_id = (
            await session.execute(text("SELECT id FROM groups ORDER BY id LIMIT 1"))
        ).scalar_one()
        # 로그인 불가능한 시스템 계정 — password_hash '!'는 어떤 해시와도 매칭 안 됨.
        row = User(
            group_id=group_id,
            username=EDITOR_USERNAME,
            password_hash="!",
            nickname=EDITOR_NICKNAME,
            email="editor@suvisdev.cloud",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return int(row.id)


async def generate_editor_reviews_once(limit: int = _DAILY_LIMIT) -> tuple[int, int]:
    """(생성 건수, 대상 건수) 반환. 수동 스크립트와 스케줄러가 공유하는 단일 경로."""
    from sqlalchemy import select

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from mova.adapter.outbound.llm.gemini_client import gemini_reply
    from mova.adapter.outbound.orm.market_reviews_orm import MovaReview
    from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie

    editor_id = await _ensure_editor_user()
    factory = get_mova_session_factory()
    async with factory() as session:
        movies = (
            await session.execute(
                select(MovaMovie.id, MovaMovie.title, MovaMovie.release_year)
                .where(
                    MovaMovie.release_year >= 2021,
                    ~MovaMovie.id.in_(
                        select(MovaReview.movie_id).where(MovaReview.user_id == editor_id)
                    ),
                )
                .order_by(MovaMovie.rating.desc())
                .limit(limit)
            )
        ).all()

    created = 0
    for movie_id, title, year in movies:
        # RSS·Gemini는 블로킹 호출 — 이벤트 루프를 막지 않게 스레드로 위임.
        articles = await asyncio.to_thread(_fetch_news, title)
        if len(articles) < 2:
            continue
        try:
            body = (
                await asyncio.to_thread(
                    gemini_reply,
                    REVIEW_PROMPT.format(title=title, year=year, articles="\n".join(articles)),
                    None,
                )
            ).strip()
        except Exception as e:  # noqa: BLE001 — 쿼터/일시 오류는 스킵하고 계속
            logger.warning("[editor-reviews] gemini 실패, 스킵: %s — %s", title, e)
            await asyncio.sleep(_GEMINI_SLEEP_SECONDS)
            continue
        if not body or "SKIP" in body[:20] or len(body) < 40:
            await asyncio.sleep(_GEMINI_SLEEP_SECONDS)
            continue

        async with factory() as session:
            session.add(
                MovaReview(user_id=editor_id, movie_id=movie_id, rating=None, body=body[:1000])
            )
            await session.commit()
        created += 1
        logger.info("[editor-reviews] 생성: %s (%d자)", title, len(body))
        await asyncio.sleep(_GEMINI_SLEEP_SECONDS)

    logger.info("[editor-reviews] 주기 완료 — 생성 %d / 대상 %d", created, len(movies))
    return created, len(movies)


async def run_editor_reviews_scheduler() -> None:
    """24시간 간격으로 에디터 리뷰를 자동 생성한다.

    개별 실패로 루프가 죽지 않도록 예외를 잡아 로깅만 하고 다음 주기로 넘어간다.
    앱 종료 시 task.cancel()이 asyncio.sleep에 CancelledError를 던져 루프가 끝난다.
    """
    while True:
        try:
            await generate_editor_reviews_once()
        except Exception as e:
            logger.warning("[editor-reviews] 주기 실행 실패: %s", e)
        await asyncio.sleep(EDITOR_REVIEWS_INTERVAL_SECONDS)
