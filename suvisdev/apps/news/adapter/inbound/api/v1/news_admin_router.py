"""운영자 API — 검색어 탭 관리와 수동 수집. require_admin(관리자 JWT)만 통과."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from shared.security.require_admin import AdminPrincipal, require_admin

from news.adapter.inbound.api.schemas.news_schema import (
    AdminTopicSchema,
    CollectReportSchema,
    TopicCreateSchema,
    TopicUpdateSchema,
)
from news.app.dtos.news_dtos import TopicCreateCommand, TopicDto, TopicUpdateCommand
from news.app.errors import DuplicateTopicError, TopicNotFoundError, TopicValidationError
from news.app.ports.input.news_use_cases import NewsCollectUseCase, NewsTopicAdminUseCase
from news.dependencies.news_provider import (
    get_news_collect_use_case,
    get_news_topic_admin_use_case,
)

news_admin_router = APIRouter(prefix="/admin", tags=["news-admin"])


def _topic(dto: TopicDto) -> AdminTopicSchema:
    return AdminTopicSchema.model_validate(asdict(dto))


@news_admin_router.get("/topics", response_model=list[AdminTopicSchema])
async def admin_list_topics(
    _admin: AdminPrincipal = Depends(require_admin),
    use_case: NewsTopicAdminUseCase = Depends(get_news_topic_admin_use_case),
) -> list[AdminTopicSchema]:
    return [_topic(t) for t in await use_case.list_topics()]


@news_admin_router.post("/topics", response_model=AdminTopicSchema, status_code=201)
async def admin_create_topic(
    payload: TopicCreateSchema,
    _admin: AdminPrincipal = Depends(require_admin),
    use_case: NewsTopicAdminUseCase = Depends(get_news_topic_admin_use_case),
) -> AdminTopicSchema:
    command = TopicCreateCommand(
        query=payload.query, label=payload.label, is_public=payload.is_public
    )
    try:
        return _topic(await use_case.create_topic(command))
    except TopicValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DuplicateTopicError as e:
        raise HTTPException(status_code=409, detail="이미 있는 검색어입니다.") from e


@news_admin_router.patch("/topics/{topic_id}", response_model=AdminTopicSchema)
async def admin_update_topic(
    topic_id: int,
    payload: TopicUpdateSchema,
    _admin: AdminPrincipal = Depends(require_admin),
    use_case: NewsTopicAdminUseCase = Depends(get_news_topic_admin_use_case),
) -> AdminTopicSchema:
    command = TopicUpdateCommand(
        topic_id=topic_id,
        label=payload.label,
        is_public=payload.is_public,
        active=payload.active,
    )
    try:
        return _topic(await use_case.update_topic(command))
    except TopicValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except TopicNotFoundError as e:
        raise HTTPException(status_code=404, detail="없는 탭입니다.") from e


@news_admin_router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_topic(
    topic_id: int,
    _admin: AdminPrincipal = Depends(require_admin),
    use_case: NewsTopicAdminUseCase = Depends(get_news_topic_admin_use_case),
) -> None:
    try:
        await use_case.delete_topic(topic_id)
    except TopicNotFoundError as e:
        raise HTTPException(status_code=404, detail="없는 탭입니다.") from e


@news_admin_router.post("/collect", response_model=CollectReportSchema)
async def admin_collect_once(
    _admin: AdminPrincipal = Depends(require_admin),
    use_case: NewsCollectUseCase = Depends(get_news_collect_use_case),
) -> CollectReportSchema:
    """수집 한 주기를 바로 돌린다 (검증·첫 적재용). 스케줄러가 꺼져 있어도 동작한다."""
    return CollectReportSchema.model_validate(asdict(await use_case.collect_once()))
