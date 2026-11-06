"""공개 읽기 — 섹션·검색어 탭 목록, 탭별 기사, 섹션별 최신, 모아 둔 기사 검색.
news.suvisdev.cloud 는 로그인 없이 이것만 쓴다. 메인은 AI 섹션, 경제는 부록.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from news.app.dtos.news_dtos import (
    ArticleDto,
    FeedSource,
    GroupDto,
    HotDto,
    SectionDto,
    TopicDto,
)
from news.app.errors import NewsQueryError, TopicNotFoundError
from news.app.ports.input.news_use_cases import NewsReadUseCase
from news.app.ports.output.news_repository import NewsRepositoryPort
from news.domain.glossary import find_terms
from news.domain.hot import HOT_COMMUNITY, HOT_PAPERS, HOT_WINDOW_HOURS
from news.domain.sections import GROUPS, SECTIONS, is_section

MAX_LIMIT = 100
MAX_QUERY_LEN = 50
MAX_TOKENS = 5


class NewsReadInteractor(NewsReadUseCase):
    def __init__(self, repository: NewsRepositoryPort, feeds: Sequence[FeedSource] = ()) -> None:
        self._repository = repository
        self._feeds = list(feeds)

    async def list_sections(self) -> list[SectionDto]:
        out: list[SectionDto] = []
        for code, label in SECTIONS.items():
            groups = [
                GroupDto(
                    code=g,
                    label=g_label,
                    feeds=[f.name for f in self._feeds if f.group == g],
                )
                for g, (g_section, g_label) in GROUPS.items()
                if g_section == code
            ]
            out.append(SectionDto(code=code, label=label, groups=groups))
        return out

    async def hot(self, limit: int) -> HotDto:
        since = datetime.now(UTC) - timedelta(hours=HOT_WINDOW_HOURS)
        n = _clamp(limit)
        return HotDto(
            papers=_with_terms(await self._repository.list_hot(HOT_PAPERS, limit=n, since=since)),
            community=_with_terms(
                await self._repository.list_hot(HOT_COMMUNITY, limit=n, since=since)
            ),
        )

    async def list_public_topics(self, section: str | None = None) -> list[TopicDto]:
        if section is not None:
            _check_section(section)
        return await self._repository.list_topics(
            public_only=True, active_only=True, section=section
        )

    async def list_topic_articles(
        self, topic_id: int, *, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        topic = await self._repository.get_topic(topic_id)
        # 비공개·꺼진 탭은 없는 것과 같게 다룬다 (존재 여부를 흘리지 않는다)
        if topic is None or not topic.is_public or not topic.active:
            raise TopicNotFoundError(topic_id)
        return _with_terms(
            await self._repository.list_topic_articles(topic_id, limit=_clamp(limit), before=before)
        )

    async def list_latest(
        self, *, section: str, group: str | None, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        _check_section(section)
        if group is not None and (group not in GROUPS or GROUPS[group][0] != section):
            raise NewsQueryError(f"{section} 섹션에 없는 묶음: {group}")
        return _with_terms(
            await self._repository.list_latest(
                section=section, group=group, limit=_clamp(limit), before=before
            )
        )

    async def search(
        self, query: str, *, section: str, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        _check_section(section)
        q = " ".join(query.split())
        if not q or len(q) > MAX_QUERY_LEN:
            raise NewsQueryError(f"검색어는 1~{MAX_QUERY_LEN}자")
        tokens = list(dict.fromkeys(q.split()))[:MAX_TOKENS]
        return _with_terms(
            await self._repository.search_articles(
                tokens, section=section, limit=_clamp(limit), before=before
            )
        )


def _with_terms(rows: list[ArticleDto]) -> list[ArticleDto]:
    """글마다 제목·요약에 나오는 사전 용어를 붙인다. 저장하지 않으니 사전을 고치면 지난 글에도 바로 반영된다."""
    return [
        replace(
            a,
            terms=find_terms(
                f"{a.title_ko or ''} {a.title} {a.summary_ko or ''} {a.summary}", a.section
            ),
        )
        for a in rows
    ]


def _check_section(section: str) -> None:
    if not is_section(section):
        raise NewsQueryError(f"없는 섹션: {section}")


def _clamp(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))
