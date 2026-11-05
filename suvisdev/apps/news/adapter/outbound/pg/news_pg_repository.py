"""news 저장소. Postgres 전용 구문(ON CONFLICT 등)을 쓰지 않아 SQLite 로도 테스트할 수 있다.
수집기는 노트북 한 곳에서만 돌므로(ENABLE_NEWS_SCHEDULER) 동시 삽입 경합은 고려하지 않는다."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime

from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from news.adapter.outbound.orm.news_orm import (
    NewsArticleOrm,
    NewsTopicArticleOrm,
    NewsTopicOrm,
    NewsVerdictOrm,
)
from news.app.dtos.news_dtos import (
    ArticleDto,
    FetchedArticle,
    StoredArticle,
    SummaryTarget,
    TopicCreateCommand,
    TopicDto,
    TopicUpdateCommand,
    VerdictCommand,
)
from news.app.ports.output.news_repository import NewsRepositoryPort
from news.domain.ko_summary import KoSummary
from news.domain.url import canonical_url

_CHUNK = 500


def _chunks[T](items: Sequence[T], size: int = _CHUNK) -> Iterator[Sequence[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _topic_dto(row: NewsTopicOrm) -> TopicDto:
    return TopicDto(
        id=row.id,
        query=row.query,
        label=row.label,
        is_public=row.is_public,
        active=row.active,
        section=row.section,
    )


class NewsPgRepository(NewsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── 검색어 탭 ──────────────────────────────────────────────
    async def list_topics(
        self, *, public_only: bool, active_only: bool, section: str | None = None
    ) -> list[TopicDto]:
        stmt = select(NewsTopicOrm).order_by(NewsTopicOrm.id)
        if public_only:
            stmt = stmt.where(NewsTopicOrm.is_public.is_(True))
        if active_only:
            stmt = stmt.where(NewsTopicOrm.active.is_(True))
        if section is not None:
            stmt = stmt.where(NewsTopicOrm.section == section)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_topic_dto(r) for r in rows]

    async def get_topic(self, topic_id: int) -> TopicDto | None:
        row = await self._session.get(NewsTopicOrm, topic_id)
        return _topic_dto(row) if row else None

    async def find_topic_by_query(self, query: str) -> TopicDto | None:
        row = (
            await self._session.execute(select(NewsTopicOrm).where(NewsTopicOrm.query == query))
        ).scalar_one_or_none()
        return _topic_dto(row) if row else None

    async def create_topic(self, command: TopicCreateCommand) -> TopicDto:
        row = NewsTopicOrm(
            query=command.query,
            label=command.label,
            section=command.section,
            is_public=command.is_public,
            active=True,
        )
        self._session.add(row)
        await self._session.flush()
        dto = _topic_dto(row)
        await self._session.commit()
        return dto

    async def update_topic(self, command: TopicUpdateCommand) -> TopicDto | None:
        row = await self._session.get(NewsTopicOrm, command.topic_id)
        if row is None:
            return None
        if command.label is not None:
            row.label = command.label
        if command.is_public is not None:
            row.is_public = command.is_public
        if command.active is not None:
            row.active = command.active
        await self._session.flush()
        dto = _topic_dto(row)
        await self._session.commit()
        return dto

    async def delete_topic(self, topic_id: int) -> bool:
        row = await self._session.get(NewsTopicOrm, topic_id)
        if row is None:
            return False
        await self._session.execute(
            delete(NewsTopicArticleOrm).where(NewsTopicArticleOrm.topic_id == topic_id)
        )
        await self._session.delete(row)
        await self._session.commit()
        return True

    # ── 기사 ──────────────────────────────────────────────────
    async def save_articles(self, items: Sequence[FetchedArticle]) -> list[StoredArticle]:
        unique: dict[str, FetchedArticle] = {}
        for item in items:
            unique.setdefault(canonical_url(item.url), item)
        urls = list(unique)

        existing: dict[str, NewsArticleOrm] = {}
        for chunk in _chunks(urls):
            rows = await self._session.execute(
                select(NewsArticleOrm).where(NewsArticleOrm.canonical_url.in_(chunk))
            )
            existing.update({r.canonical_url: r for r in rows.scalars()})

        now = datetime.now(UTC)
        new_urls: set[str] = set()
        for url, item in unique.items():
            if url in existing:
                continue
            row = NewsArticleOrm(
                canonical_url=url,
                link=item.link,
                source_domain=item.source_domain[:200],
                source_name=item.source_name[:100] if item.source_name else None,
                title=item.title[:500],
                summary=item.summary,
                body=item.body,
                author=item.author[:100],
                origin=item.origin,
                section=item.section,
                feed_group=item.group,
                published_at=item.published_at,
                sort_at=item.published_at or now,
            )
            self._session.add(row)
            existing[url] = row
            new_urls.add(url)
        await self._session.flush()

        stored = [
            StoredArticle(
                id=existing[url].id,
                url=url,
                title=existing[url].title,
                summary=existing[url].summary,
                body=existing[url].body,
                source_domain=existing[url].source_domain,
                source_name=existing[url].source_name,
                author=existing[url].author,
                is_new=url in new_urls,
                section=existing[url].section,
                group=existing[url].feed_group,
            )
            for url in urls
        ]
        await self._session.commit()
        return stored

    async def link_topic_articles(self, topic_id: int, pairs: Sequence[tuple[int, float]]) -> None:
        if not pairs:
            return
        ids = [a for a, _ in pairs]
        have: set[int] = set()
        for chunk in _chunks(ids):
            rows = await self._session.execute(
                select(NewsTopicArticleOrm.article_id).where(
                    NewsTopicArticleOrm.topic_id == topic_id,
                    NewsTopicArticleOrm.article_id.in_(chunk),
                )
            )
            have.update(rows.scalars())
        for article_id, score in pairs:
            if article_id not in have:
                self._session.add(
                    NewsTopicArticleOrm(topic_id=topic_id, article_id=article_id, relevance=score)
                )
        await self._session.commit()

    async def missing_verdicts(
        self, article_ids: Sequence[int], harness_version: str, layer: str
    ) -> set[int]:
        done: set[int] = set()
        for chunk in _chunks(list(article_ids)):
            rows = await self._session.execute(
                select(NewsVerdictOrm.article_id).where(
                    NewsVerdictOrm.layer == layer,
                    NewsVerdictOrm.harness_version == harness_version,
                    NewsVerdictOrm.article_id.in_(chunk),
                )
            )
            done.update(rows.scalars())
        return set(article_ids) - done

    async def save_verdicts(self, commands: Sequence[VerdictCommand]) -> None:
        for layer in {c.layer for c in commands}:
            group = [c for c in commands if c.layer == layer]
            existing: dict[int, NewsVerdictOrm] = {}
            for chunk in _chunks([c.article_id for c in group]):
                rows = await self._session.execute(
                    select(NewsVerdictOrm).where(
                        NewsVerdictOrm.layer == layer, NewsVerdictOrm.article_id.in_(chunk)
                    )
                )
                existing.update({r.article_id: r for r in rows.scalars()})
            for c in group:
                row = existing.get(c.article_id)
                if row is None:
                    row = NewsVerdictOrm(article_id=c.article_id, layer=layer)
                    self._session.add(row)
                row.harness_version = c.harness_version
                row.verdict = c.verdict
                row.badge = c.badge
                row.reasons_ko = c.reasons_ko
                row.signals = c.signals
        await self._session.commit()

    async def list_topic_articles(
        self, topic_id: int, *, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        stmt = (
            select(NewsArticleOrm)
            .join(NewsTopicArticleOrm, NewsTopicArticleOrm.article_id == NewsArticleOrm.id)
            .where(NewsTopicArticleOrm.topic_id == topic_id)
        )
        if before is not None:
            stmt = stmt.where(NewsArticleOrm.sort_at < before)
        stmt = stmt.order_by(NewsArticleOrm.sort_at.desc(), NewsArticleOrm.id.desc()).limit(limit)
        return await self._with_badges(list((await self._session.execute(stmt)).scalars()))

    async def list_latest(
        self, *, section: str, group: str | None, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        stmt = select(NewsArticleOrm).where(
            NewsArticleOrm.origin == "feed", NewsArticleOrm.section == section
        )
        if group is not None:
            stmt = stmt.where(NewsArticleOrm.feed_group == group)
        if before is not None:
            stmt = stmt.where(NewsArticleOrm.sort_at < before)
        stmt = stmt.order_by(NewsArticleOrm.sort_at.desc(), NewsArticleOrm.id.desc()).limit(limit)
        return await self._with_badges(list((await self._session.execute(stmt)).scalars()))

    async def search_articles(
        self, tokens: Sequence[str], *, section: str, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        stmt = select(NewsArticleOrm).where(NewsArticleOrm.section == section)
        for tok in tokens:
            needle = tok.lower()
            # 한국어 제목·요약도 찾는다 — 영어 논문을 "전문가 혼합" 같은 한국어로 찾을 수 있게
            stmt = stmt.where(
                or_(
                    func.lower(NewsArticleOrm.title).contains(needle, autoescape=True),
                    func.lower(NewsArticleOrm.summary).contains(needle, autoescape=True),
                    func.lower(NewsArticleOrm.title_ko).contains(needle, autoescape=True),
                    func.lower(NewsArticleOrm.summary_ko).contains(needle, autoescape=True),
                )
            )
        if before is not None:
            stmt = stmt.where(NewsArticleOrm.sort_at < before)
        stmt = stmt.order_by(NewsArticleOrm.sort_at.desc(), NewsArticleOrm.id.desc()).limit(limit)
        return await self._with_badges(list((await self._session.execute(stmt)).scalars()))

    async def _with_badges(self, rows: list[NewsArticleOrm]) -> list[ArticleDto]:
        verdicts: dict[int, dict[str, NewsVerdictOrm]] = {}
        if rows:
            found = await self._session.execute(
                select(NewsVerdictOrm).where(NewsVerdictOrm.article_id.in_([r.id for r in rows]))
            )
            for v in found.scalars():
                verdicts.setdefault(v.article_id, {})[v.layer] = v
        out: list[ArticleDto] = []
        for r in rows:
            layers = verdicts.get(r.id, {})
            chosen = layers.get("llm") or layers.get("rules")  # 2차 판정이 있으면 그것을 따른다
            out.append(
                ArticleDto(
                    id=r.id,
                    title=r.title,
                    url=r.canonical_url,
                    summary=r.summary,
                    source_domain=r.source_domain,
                    source_name=r.source_name,
                    published_at=r.published_at,
                    badge=chosen.badge if chosen else "none",
                    reasons_ko=list(chosen.reasons_ko) if chosen else [],
                    section=r.section,
                    group=r.feed_group,
                    sort_at=r.sort_at,
                    title_ko=r.title_ko,
                    summary_ko=r.summary_ko,
                )
            )
        return out

    # ── 한국어 제목·요약 ───────────────────────────────────────
    async def pending_summaries(self, *, limit: int, max_tries: int) -> list[SummaryTarget]:
        ai_first = case((NewsArticleOrm.section == "ai", 0), else_=1)
        stmt = (
            select(NewsArticleOrm)
            .where(NewsArticleOrm.summary_ko.is_(None), NewsArticleOrm.ko_tries < max_tries)
            .order_by(ai_first, NewsArticleOrm.sort_at.desc(), NewsArticleOrm.id.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            SummaryTarget(
                id=r.id,
                title=r.title,
                summary=r.summary,
                body=r.body,
                source_name=r.source_name,
                section=r.section,
            )
            for r in rows
        ]

    async def save_summary(self, article_id: int, summary: KoSummary, model: str) -> None:
        await self._session.execute(
            update(NewsArticleOrm)
            .where(NewsArticleOrm.id == article_id)
            .values(
                title_ko=summary.title_ko,
                summary_ko=summary.summary_ko,
                ko_model=model[:40],
                ko_at=datetime.now(UTC),
            )
        )
        await self._session.commit()

    async def mark_summary_failed(self, article_id: int) -> None:
        await self._session.execute(
            update(NewsArticleOrm)
            .where(NewsArticleOrm.id == article_id)
            .values(ko_tries=NewsArticleOrm.ko_tries + 1)
        )
        await self._session.commit()
