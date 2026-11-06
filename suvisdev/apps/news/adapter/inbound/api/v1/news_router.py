"""공개 읽기 API — news.suvisdev.cloud 화면이 로그인 없이 쓴다.

메인은 AI 섹션(section=ai, 기본값), 경제는 부록(section=economy). 검색은 모아 둔 기사에서만 찾는다.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from news.adapter.inbound.api.schemas.news_schema import (
    ArticleSchema,
    HotSchema,
    SectionCode,
    SectionSchema,
    TopicSchema,
)
from news.app.dtos.news_dtos import ArticleDto
from news.app.errors import NewsQueryError, TopicNotFoundError
from news.app.ports.input.news_use_cases import NewsReadUseCase
from news.dependencies.news_provider import get_news_read_use_case

news_router = APIRouter(tags=["news"])

_BEFORE_DESC = "이 시각보다 오래된 기사 (다음 페이지)"
_SECTION_DESC = "ai(메인) · economy(부록)"


def _article(dto: ArticleDto) -> ArticleSchema:
    return ArticleSchema.model_validate(asdict(dto))


@news_router.get("/sections", response_model=list[SectionSchema])
async def list_sections(
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> list[SectionSchema]:
    return [SectionSchema.model_validate(asdict(s)) for s in await use_case.list_sections()]


@news_router.get("/hot", response_model=HotSchema)
async def get_hot(
    limit: int = Query(default=3, ge=1, le=20),
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> HotSchema:
    hot = await use_case.hot(limit)
    return HotSchema(
        papers=[_article(a) for a in hot.papers],
        community=[_article(a) for a in hot.community],
    )


@news_router.get("/topics", response_model=list[TopicSchema])
async def list_topics(
    section: SectionCode | None = Query(default=None, description=_SECTION_DESC),
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> list[TopicSchema]:
    topics = await use_case.list_public_topics(section)
    return [
        TopicSchema.model_validate(
            {"id": t.id, "label": t.label, "query": t.query, "section": t.section}
        )
        for t in topics
    ]


@news_router.get("/topics/{topic_id}/articles", response_model=list[ArticleSchema])
async def list_topic_articles(
    topic_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    before: datetime | None = Query(default=None, description=_BEFORE_DESC),
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> list[ArticleSchema]:
    try:
        rows = await use_case.list_topic_articles(topic_id, limit=limit, before=before)
    except TopicNotFoundError as e:
        raise HTTPException(status_code=404, detail="없는 탭입니다.") from e
    return [_article(r) for r in rows]


@news_router.get("/latest", response_model=list[ArticleSchema])
async def list_latest(
    section: SectionCode = Query(default="ai", description=_SECTION_DESC),
    group: str | None = Query(default=None, max_length=16, description="출처 묶음 (/sections)"),
    limit: int = Query(default=30, ge=1, le=100),
    before: datetime | None = Query(default=None, description=_BEFORE_DESC),
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> list[ArticleSchema]:
    try:
        rows = await use_case.list_latest(section=section, group=group, limit=limit, before=before)
    except NewsQueryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return [_article(r) for r in rows]


@news_router.get("/search", response_model=list[ArticleSchema])
async def search_articles(
    q: str = Query(..., min_length=1, max_length=50, description="제목·요약에 모두 들어갈 단어"),
    section: SectionCode = Query(default="ai", description=_SECTION_DESC),
    limit: int = Query(default=30, ge=1, le=100),
    before: datetime | None = Query(default=None, description=_BEFORE_DESC),
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> list[ArticleSchema]:
    try:
        rows = await use_case.search(q, section=section, limit=limit, before=before)
    except NewsQueryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return [_article(r) for r in rows]
