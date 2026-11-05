"""테스트용 가짜 포트 — DB·네트워크 없이 인터랙터를 돌린다."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from news.app.dtos.news_dtos import (
    ArticleDto,
    FeedSource,
    FetchedArticle,
    StoredArticle,
    TopicCreateCommand,
    TopicDto,
    TopicUpdateCommand,
    VerdictCommand,
)
from news.app.ports.output.news_repository import NewsRepositoryPort
from news.app.ports.output.news_source_ports import FeedReaderPort, NewsSearchPort
from news.domain.url import canonical_url


class FakeRepo(NewsRepositoryPort):
    def __init__(self) -> None:
        self.topics: dict[int, TopicDto] = {}
        self.articles: dict[str, StoredArticle] = {}
        self.links: dict[int, dict[int, float]] = {}
        self.verdicts: dict[tuple[int, str], VerdictCommand] = {}
        self.last_query: tuple[object, ...] = ()

    async def list_topics(
        self, *, public_only: bool, active_only: bool, section: str | None = None
    ) -> list[TopicDto]:
        return [
            t
            for t in self.topics.values()
            if (not public_only or t.is_public)
            and (not active_only or t.active)
            and (section is None or t.section == section)
        ]

    async def get_topic(self, topic_id: int) -> TopicDto | None:
        return self.topics.get(topic_id)

    async def find_topic_by_query(self, query: str) -> TopicDto | None:
        return next((t for t in self.topics.values() if t.query == query), None)

    async def create_topic(self, command: TopicCreateCommand) -> TopicDto:
        t = TopicDto(
            len(self.topics) + 1,
            command.query,
            command.label,
            command.is_public,
            True,
            command.section,
        )
        self.topics[t.id] = t
        return t

    async def update_topic(self, command: TopicUpdateCommand) -> TopicDto | None:
        t = self.topics.get(command.topic_id)
        if t is None:
            return None
        t = replace(
            t,
            label=command.label if command.label is not None else t.label,
            is_public=command.is_public if command.is_public is not None else t.is_public,
            active=command.active if command.active is not None else t.active,
        )
        self.topics[t.id] = t
        return t

    async def delete_topic(self, topic_id: int) -> bool:
        return self.topics.pop(topic_id, None) is not None

    async def save_articles(self, items: Sequence[FetchedArticle]) -> list[StoredArticle]:
        out = []
        for it in items:
            url = canonical_url(it.url)
            if url in self.articles:
                out.append(replace(self.articles[url], is_new=False))
                continue
            s = StoredArticle(
                id=len(self.articles) + 1,
                url=url,
                title=it.title,
                summary=it.summary,
                body=it.body,
                source_domain=it.source_domain,
                source_name=it.source_name,
                author=it.author,
                is_new=True,
                section=it.section,
                group=it.group,
            )
            self.articles[url] = s
            out.append(s)
        return out

    async def link_topic_articles(self, topic_id: int, pairs: Sequence[tuple[int, float]]) -> None:
        self.links.setdefault(topic_id, {}).update(dict(pairs))

    async def missing_verdicts(
        self, article_ids: Sequence[int], harness_version: str, layer: str
    ) -> set[int]:
        return {
            a
            for a in article_ids
            if (a, layer) not in self.verdicts
            or self.verdicts[(a, layer)].harness_version != harness_version
        }

    async def save_verdicts(self, commands: Sequence[VerdictCommand]) -> None:
        for c in commands:
            self.verdicts[(c.article_id, c.layer)] = c

    async def list_topic_articles(
        self, topic_id: int, *, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        return []

    async def list_latest(
        self, *, section: str, group: str | None, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        self.last_query = ("latest", section, group, limit)
        return []

    async def search_articles(
        self, tokens: Sequence[str], *, section: str, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        self.last_query = ("search", section, tuple(tokens), limit)
        return []


class FakeSearch(NewsSearchPort):
    def __init__(self, results: dict[str, list[FetchedArticle]], enabled: bool = True) -> None:
        self._results = results
        self._enabled = enabled
        self.calls: list[str] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def search(self, query: str, display: int = 100) -> list[FetchedArticle]:
        self.calls.append(query)
        if query == "터짐":
            raise RuntimeError("429 Too Many Requests")
        return self._results.get(query, [])


class FakeFeeds(FeedReaderPort):
    def __init__(self, results: dict[str, list[FetchedArticle]]) -> None:
        self._results = results

    async def read(self, feed: FeedSource) -> list[FetchedArticle]:
        if feed.name not in self._results:
            raise RuntimeError("404")
        return self._results[feed.name]


def art(
    url: str, title: str, summary: str = "", origin: str = "search", **kw: str
) -> FetchedArticle:
    """기사 하나. RSS 기사(origin=feed)는 group 을 안 주면 경제 언론(outlet)으로 본다."""
    from news.domain.sections import section_of_group
    from news.domain.url import domain_of_url

    if origin == "feed":
        kw.setdefault("group", "outlet")
    if kw.get("group"):
        kw.setdefault("section", section_of_group(kw["group"]))
    return FetchedArticle(
        url=url,
        title=title,
        summary=summary,
        source_domain=domain_of_url(url),
        origin=origin,
        **kw,  # type: ignore[arg-type]
    )
