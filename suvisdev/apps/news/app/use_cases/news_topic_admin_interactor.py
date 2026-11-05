"""운영자 검색어 탭 관리 — suvisdev.cloud/admin 에서 로그인한 관리자만 (라우터가 require_admin)."""

from __future__ import annotations

from dataclasses import replace

from news.app.dtos.news_dtos import TopicCreateCommand, TopicDto, TopicUpdateCommand
from news.app.errors import DuplicateTopicError, TopicNotFoundError, TopicValidationError
from news.app.ports.input.news_use_cases import NewsTopicAdminUseCase
from news.app.ports.output.news_repository import NewsRepositoryPort

MAX_QUERY_LEN = 100
MAX_LABEL_LEN = 50


class NewsTopicAdminInteractor(NewsTopicAdminUseCase):
    def __init__(self, repository: NewsRepositoryPort) -> None:
        self._repository = repository

    async def list_topics(self) -> list[TopicDto]:
        return await self._repository.list_topics(public_only=False, active_only=False)

    async def create_topic(self, command: TopicCreateCommand) -> TopicDto:
        query = " ".join(command.query.split())
        label = " ".join(command.label.split()) or query
        if not query or len(query) > MAX_QUERY_LEN:
            raise TopicValidationError(f"검색어는 1~{MAX_QUERY_LEN}자")
        if len(label) > MAX_LABEL_LEN:
            raise TopicValidationError(f"탭 이름은 {MAX_LABEL_LEN}자 이하")
        if await self._repository.find_topic_by_query(query) is not None:
            raise DuplicateTopicError(query)
        return await self._repository.create_topic(replace(command, query=query, label=label))

    async def update_topic(self, command: TopicUpdateCommand) -> TopicDto:
        if command.label is not None:
            label = " ".join(command.label.split())
            if not label or len(label) > MAX_LABEL_LEN:
                raise TopicValidationError(f"탭 이름은 1~{MAX_LABEL_LEN}자")
            command = replace(command, label=label)
        updated = await self._repository.update_topic(command)
        if updated is None:
            raise TopicNotFoundError(command.topic_id)
        return updated

    async def delete_topic(self, topic_id: int) -> None:
        if not await self._repository.delete_topic(topic_id):
            raise TopicNotFoundError(topic_id)
