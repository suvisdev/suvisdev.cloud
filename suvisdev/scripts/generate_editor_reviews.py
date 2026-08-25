"""뉴스 크롤링 기반 "Mova 에디터" 리뷰 자동 생성 배치.

구글 뉴스 RSS(제목+요약만 — 기사 원문 미수집, 저작권 원칙은 GoogleNewsScraper와
동일)에서 영화별 언론 반응을 모아 Gemini로 3~4문장 리뷰를 생성하고, 시스템
계정("Mova 에디터")으로 reviews에 저장한다. UNIQUE(user_id, movie_id) 덕에
영화당 에디터 리뷰는 1건 — 이미 있으면 스킵해 재실행이 안전하다.

Usage (backend 컨테이너 안):
  docker exec suvisdevcloud-backend-1 python scripts/generate_editor_reviews.py --limit 20
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from urllib.parse import quote

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

EDITOR_USERNAME = "mova_editor"
EDITOR_NICKNAME = "Mova 에디터"
_FEED_URL = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
_GEMINI_SLEEP = 4.5  # 무료 티어 15req/min

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


async def main(limit: int) -> None:
    from sqlalchemy import select, text

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from mova.adapter.outbound.llm.gemini_client import gemini_reply
    from mova.adapter.outbound.orm.market_reviews_orm import MovaReview
    from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
    from viewer.adapter.outbound.orm.user_orm import User

    factory = get_mova_session_factory()

    async with factory() as session:
        # 시스템 계정 확보 — 로그인 불가능한 계정(password_hash '!')로 생성.
        editor_id = (
            await session.execute(select(User.id).where(User.username == EDITOR_USERNAME))
        ).scalar_one_or_none()
        if editor_id is None:
            group_id = (
                await session.execute(text("SELECT id FROM groups ORDER BY id LIMIT 1"))
            ).scalar_one()
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
            editor_id = row.id
        print(f"[editor-reviews] 에디터 user_id={editor_id}")

        # 최근 5년 인기작 중 에디터 리뷰가 아직 없는 영화
        movies = (
            (
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
            )
            .all()
        )
    print(f"[editor-reviews] 대상 {len(movies)}편")

    created = 0
    for movie_id, title, year in movies:
        articles = _fetch_news(title)
        if len(articles) < 2:
            print(f"  skip(기사 부족): {title}")
            continue
        try:
            body = gemini_reply(
                REVIEW_PROMPT.format(title=title, year=year, articles="\n".join(articles)),
                None,
            ).strip()
        except Exception as e:  # noqa: BLE001 — 쿼터/일시 오류는 스킵하고 계속
            print(f"  skip(gemini 오류): {title} — {e}")
            time.sleep(_GEMINI_SLEEP)
            continue
        if not body or "SKIP" in body[:20] or len(body) < 40:
            print(f"  skip(무관/짧음): {title}")
            time.sleep(_GEMINI_SLEEP)
            continue

        async with factory() as session:
            session.add(
                MovaReview(user_id=editor_id, movie_id=movie_id, rating=None, body=body[:1000])
            )
            await session.commit()
        created += 1
        print(f"  ok: {title} ({len(body)}자)")
        time.sleep(_GEMINI_SLEEP)

    print(f"[editor-reviews] DONE — 생성 {created} / 대상 {len(movies)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(main(args.limit))
