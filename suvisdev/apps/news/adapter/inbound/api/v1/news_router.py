"""공개 읽기 API — news.suvisdev.cloud 화면이 로그인 없이 쓴다."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from news.adapter.inbound.api.schemas.news_schema import ArticleSchema, TopicSchema
from news.app.dtos.news_dtos import ArticleDto
from news.app.errors import TopicNotFoundError
from news.app.ports.input.news_use_cases import NewsReadUseCase
from news.dependencies.news_provider import get_news_read_use_case

news_router = APIRouter(tags=["news"])

_BEFORE_DESC = "이 시각보다 오래된 기사 (다음 페이지)"


def _article(dto: ArticleDto) -> ArticleSchema:
    return ArticleSchema.model_validate(asdict(dto))


@news_router.get("/topics", response_model=list[TopicSchema])
async def list_topics(
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> list[TopicSchema]:
    topics = await use_case.list_public_topics()
    return [TopicSchema(id=t.id, label=t.label, query=t.query) for t in topics]


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
    limit: int = Query(default=30, ge=1, le=100),
    before: datetime | None = Query(default=None, description=_BEFORE_DESC),
    use_case: NewsReadUseCase = Depends(get_news_read_use_case),
) -> list[ArticleSchema]:
    return [_article(r) for r in await use_case.list_latest(limit=limit, before=before)]
