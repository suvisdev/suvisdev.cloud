"""저장소 SQL — 메모리 SQLite 로 돌린다(운영은 Postgres). aiosqlite 가 없으면 건너뛴다(CI 포함)."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from news.adapter.outbound.orm.base import NewsBase  # noqa: E402
from news.adapter.outbound.pg.news_pg_repository import NewsPgRepository  # noqa: E402
from news.app.dtos.news_dtos import (  # noqa: E402
    FetchedArticle,
    HotUpdate,
    TopicCreateCommand,
    TopicUpdateCommand,
    VerdictCommand,
)


@pytest_asyncio.fixture
async def repo():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(NewsBase.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield NewsPgRepository(session)
    await engine.dispose()


def _a(
    n: int,
    origin: str = "feed",
    minutes: int = 0,
    section: str = "ai",
    group: str = "lab",
    title: str | None = None,
    summary: str = "요약",
) -> FetchedArticle:
    return FetchedArticle(
        url=f"https://a.example/{n}?utm_source=x",
        title=title or f"기사 {n}",
        summary=summary,
        source_domain="a.example",
        origin=origin,
        published_at=datetime(2026, 11, 5, 9, tzinfo=UTC) + timedelta(minutes=minutes),
        section=section,
        group=group,
    )


@pytest.mark.asyncio
async def test_save_articles_is_idempotent_by_canonical_url(repo):
    first = await repo.save_articles([_a(1), _a(2), _a(1)])
    assert [s.is_new for s in first] == [True, True]
    again = await repo.save_articles([_a(1), _a(3)])
    assert [s.is_new for s in again] == [False, True]
    assert again[0].id == first[0].id and again[0].url == "https://a.example/1"


@pytest.mark.asyncio
async def test_topic_articles_with_badges_and_paging(repo):
    topic = await repo.create_topic(TopicCreateCommand(query="반도체", label="반도체"))
    stored = await repo.save_articles([_a(1, "search", 0), _a(2, "search", 10), _a(3, "feed", 20)])
    await repo.link_topic_articles(topic.id, [(stored[0].id, 1.0), (stored[1].id, 0.6)])
    await repo.link_topic_articles(topic.id, [(stored[0].id, 1.0)])  # 중복 연결은 무시
    await repo.save_verdicts(
        [
            VerdictCommand(
                stored[1].id, "rules", "0.1.0", "ai", "ai_suspected", ["기자 이름이 없음"], []
            ),
            VerdictCommand(stored[0].id, "rules", "0.1.0", "normal", "none", [], []),
        ]
    )
    rows = await repo.list_topic_articles(topic.id, limit=10, before=None)
    assert [r.title for r in rows] == ["기사 2", "기사 1"]  # 최신순
    assert rows[0].badge == "ai_suspected" and rows[1].badge == "none"
    older = await repo.list_topic_articles(topic.id, limit=10, before=rows[0].published_at)
    assert [r.title for r in older] == ["기사 1"]
    latest = await repo.list_latest(section="ai", group=None, limit=10, before=None)
    assert [r.title for r in latest] == ["기사 3"]  # 최신 탭은 RSS 기사만


@pytest.mark.asyncio
async def test_latest_by_section_and_group(repo):
    await repo.save_articles(
        [
            _a(1, minutes=0, group="lab"),
            _a(2, minutes=10, group="paper"),
            _a(3, minutes=20, section="economy", group="outlet"),
        ]
    )
    ai = await repo.list_latest(section="ai", group=None, limit=10, before=None)
    assert [(r.title, r.group) for r in ai] == [("기사 2", "paper"), ("기사 1", "lab")]
    papers = await repo.list_latest(section="ai", group="paper", limit=10, before=None)
    assert [r.title for r in papers] == ["기사 2"]
    econ = await repo.list_latest(section="economy", group=None, limit=10, before=None)
    assert [(r.title, r.section) for r in econ] == [("기사 3", "economy")]


@pytest.mark.asyncio
async def test_search_matches_all_tokens_case_insensitive_within_section(repo):
    await repo.save_articles(
        [
            _a(1, minutes=0, title="Sparse Mixture of Experts", summary="routing"),
            _a(2, minutes=10, title="Dense model", summary="no MIXTURE here"),
            _a(3, minutes=20, title="금리 인하 기대", section="economy", group="outlet"),
            _a(4, minutes=30, title="100% 달성", section="economy", group="outlet"),
        ]
    )
    rows = await repo.search_articles(["mixture"], section="ai", limit=10, before=None)
    assert [r.title for r in rows] == ["Dense model", "Sparse Mixture of Experts"]  # 요약도 본다
    rows = await repo.search_articles(["Mixture", "routing"], section="ai", limit=10, before=None)
    assert [r.title for r in rows] == ["Sparse Mixture of Experts"]
    assert await repo.search_articles(["금리"], section="ai", limit=10, before=None) == []
    rows = await repo.search_articles(["금리"], section="economy", limit=10, before=None)
    assert [r.title for r in rows] == ["금리 인하 기대"]
    rows = await repo.search_articles(["%"], section="economy", limit=10, before=None)
    assert [r.title for r in rows] == ["100% 달성"]  # LIKE 특수문자는 글자 그대로


@pytest.mark.asyncio
async def test_llm_verdict_overrides_rules_and_version_tracking(repo):
    (s,) = await repo.save_articles([_a(1)])
    await repo.save_verdicts([VerdictCommand(s.id, "rules", "0.1.0", "pending", "none", [], [])])
    assert await repo.missing_verdicts([s.id], "0.1.0", "rules") == set()
    assert await repo.missing_verdicts([s.id], "0.2.0", "rules") == {s.id}
    await repo.save_verdicts(
        [
            VerdictCommand(
                s.id, "llm", "0.1.0", "ai", "ai_suspected", ["인용이나 출처 표기가 없음"], []
            )
        ]
    )
    (row,) = await repo.list_latest(section="ai", group=None, limit=5, before=None)
    assert row.badge == "ai_suspected"


@pytest.mark.asyncio
async def test_topic_crud(repo):
    t = await repo.create_topic(
        TopicCreateCommand(query="환율", label="환율", is_public=False, section="economy")
    )
    assert await repo.find_topic_by_query("환율") == t and t.section == "economy"
    assert await repo.list_topics(public_only=True, active_only=True) == []
    assert await repo.list_topics(public_only=False, active_only=True, section="ai") == []
    u = await repo.update_topic(
        TopicUpdateCommand(topic_id=t.id, is_public=True, label="환율 소식")
    )
    assert u is not None and u.label == "환율 소식" and u.is_public
    assert await repo.delete_topic(t.id) is True
    assert await repo.delete_topic(t.id) is False


@pytest.mark.asyncio
async def test_digest_candidates_keep_window_and_only_hot_papers(repo):
    saved = await repo.save_articles(
        [
            _a(1, group="community"),
            _a(2, group="paper"),
            _a(3, group="paper"),
            _a(4, group="lab", minutes=24 * 60),  # 기간 밖
            _a(5, group="outlet", section="economy"),
            _a(6, origin="search", group="community"),
        ]
    )
    await repo.set_hot([HotUpdate(article_id=saved[2].id, source="hf", score=9, label="추천 9")])
    rows = await repo.list_digest_candidates(
        since=datetime(2026, 11, 5, 0, tzinfo=UTC), until=datetime(2026, 11, 6, 0, tzinfo=UTC)
    )
    assert {r.url for r in rows} == {"https://a.example/1", "https://a.example/3"}
