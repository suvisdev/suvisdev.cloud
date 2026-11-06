"""오늘의 핫한 소식 — 규칙, 출처 어댑터(가짜 전송), 인터랙터, 저장소(SQLite), 내용 없는 글 처리."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from news_fakes import FakeRepo, art

from news.adapter.outbound.http.hot_sources import (
    HackerNewsSource,
    HuggingFacePapersSource,
    parse_hf_papers,
    parse_hn_hits,
)
from news.adapter.outbound.llm.ollama_ko_summarizer import OllamaKoSummarizer
from news.app.dtos.news_dtos import FetchedArticle, HotItem, HotUpdate, SummaryTarget
from news.app.ports.output.news_source_ports import HotSourcePort
from news.app.use_cases.news_hot_interactor import NewsHotInteractor
from news.app.use_cases.news_read_interactor import NewsReadInteractor
from news.domain.feed_text import clean_feed_summary, has_enough_text
from news.domain.hot import (
    HOT_COMMUNITY,
    HOT_PAPERS,
    HOT_WINDOW_HOURS,
    community_label,
    is_ai_title,
    papers_label,
)
from news.domain.ko_summary import KoSummary, parse_title_only

_HN_SHELL = (
    "Article URL: https://martinfowler.com/x Comments URL: https://news.ycombinator.com/item?id=1 "
    "Points: 611 # Comments: 336"
)
_REDDIT_SHELL = "submitted by /u/someone [link] [comments]"


# ── 내용 없는 글 ──────────────────────────────────────────
@pytest.mark.parametrize("shell", [_HN_SHELL, _REDDIT_SHELL, "[link] [comments]", "", "   "])
def test_shell_only_summary_has_no_content(shell):
    assert clean_feed_summary(shell) == ""
    assert not has_enough_text(shell)


def test_real_text_survives_cleaning():
    reddit = "I benchmarked Kimi K3 on a single RTX 4060 and it holds up well. submitted by /u/a [link] [comments]"
    assert clean_feed_summary(reddit).endswith("holds up well.")
    assert has_enough_text(reddit)
    assert has_enough_text(_HN_SHELL, "본문이 따로 있으면 요약할 수 있다. " * 3)
    assert not has_enough_text("짧은 한 줄")


def test_parse_title_only():
    assert parse_title_only('{"title_ko": "LLM 말투"}', "LLM Voice") == KoSummary("LLM 말투", "")
    assert parse_title_only('{"title_ko": "Other words"}', "LLM Voice") == KoSummary(
        "LLM Voice", ""
    )
    assert parse_title_only('{"title_ko": ""}', "LLM Voice") is None
    assert parse_title_only("not json", "LLM Voice") is None


def _target(title: str, summary: str = "") -> SummaryTarget:
    return SummaryTarget(id=1, title=title, summary=summary, body="", source_name="x", section="ai")


@pytest.mark.asyncio
async def test_adapter_never_asks_model_to_summarize_empty_posts():
    prompts: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        prompts.append(json.loads(req.content)["messages"][1]["content"])
        content = json.dumps({"title_ko": "LLM 말투"}, ensure_ascii=False)
        return httpx.Response(200, json={"message": {"content": content}})

    s = OllamaKoSummarizer(base_url="http://x.test", transport=httpx.MockTransport(handler))

    # 한국어 제목 + 내용 없음 → 모델을 부르지 않는다
    out = await s.summarize(_target("오픈AI 소식", ""))
    assert out == KoSummary("오픈AI 소식", "") and prompts == []

    # 영어 제목 + 껍데기뿐 → 제목만 옮긴다. 요약은 만들지 않는다
    out = await s.summarize(_target("LLM Voice", _REDDIT_SHELL))
    assert out == KoSummary("LLM 말투", "")
    assert prompts == ["제목: LLM Voice"]


# ── 규칙 ─────────────────────────────────────────────────
@pytest.mark.parametrize(
    "title",
    [
        "Show HN: a local LLM runner",
        "Claude Code now supports plugins",
        "GPT-5.5 system card",
        "Why agentic coding fails",
        "OpenAI buys something",
        "AI is eating the world",
    ],
)
def test_ai_titles(title):
    assert is_ai_title(title)


@pytest.mark.parametrize(
    "title",
    [
        "A new Rust web framework",
        "Maine's lobster industry",
        "The paint is still wet",
        "Said no one",
    ],
)
def test_not_ai_titles(title):
    assert not is_ai_title(title)


def test_labels():
    assert papers_label(83) == "추천 83"
    assert community_label(1267, 741) == "1,267점 · 댓글 741"


# ── 출처 어댑터 ───────────────────────────────────────────
def _paper(pid: str, upvotes: int, title: str = "Sparse Experts") -> dict[str, object]:
    return {
        "title": title,
        "publishedAt": "2026-11-05T12:00:00.000Z",
        "paper": {
            "id": pid,
            "title": title,
            "summary": "We study  sparse experts.",
            "upvotes": upvotes,
        },
    }


def test_parse_hf_sorts_dedups_and_uses_arxiv_url():
    items = parse_hf_papers(
        [_paper("2611.1", 5), _paper("2611.2", 83), _paper("2611.1", 5), {"paper": {"id": ""}}]
    )
    assert [i.score for i in items] == [83, 5]
    top = items[0]
    assert (
        top.article.url == "https://arxiv.org/abs/2611.2"
    )  # arXiv RSS 와 같은 주소라 한 글로 합쳐진다
    assert top.article.group == "paper" and top.article.section == "ai"
    assert top.article.summary == "We study sparse experts."
    assert top.source == HOT_PAPERS and top.label == "추천 83"
    assert top.article.published_at == datetime(2026, 11, 5, 12, tzinfo=UTC)


def test_parse_hn_filters_non_ai_and_links_to_comments_without_url():
    hits = [
        {
            "title": "A new Rust web framework",
            "url": "https://r.example",
            "points": 900,
            "objectID": "1",
        },
        {
            "title": "Claude Code tips",
            "url": "https://c.example/a?utm_source=hn",
            "points": 300,
            "num_comments": 40,
            "objectID": "2",
            "created_at_i": 1793000000,
        },
        {
            "title": "Ask HN: How do you run LLMs?",
            "url": None,
            "points": 150,
            "num_comments": 1200,
            "objectID": "3",
            "story_text": "<p>I run them <b>locally</b>.</p>",
        },
    ]
    items = parse_hn_hits(hits)
    assert [i.article.title for i in items] == ["Claude Code tips", "Ask HN: How do you run LLMs?"]
    ask = items[1]
    assert ask.article.url == "https://news.ycombinator.com/item?id=3"
    assert ask.article.summary == "I run them locally ."
    assert ask.article.group == "community" and ask.source == HOT_COMMUNITY
    assert ask.label == "150점 · 댓글 1,200"
    assert items[0].article.published_at == datetime.fromtimestamp(1793000000, UTC)


@pytest.mark.asyncio
async def test_hf_source_asks_today_and_yesterday():
    dates: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        dates.append(req.url.params["date"])
        assert req.headers["user-agent"].startswith("suvisdev-news")
        return httpx.Response(200, json=[_paper(f"2611.{len(dates)}", len(dates))])

    items = await HuggingFacePapersSource(transport=httpx.MockTransport(handler)).fetch()
    assert len(dates) == 2 and dates[0] > dates[1]
    assert [i.score for i in items] == [2, 1]


@pytest.mark.asyncio
async def test_hn_source_filters_by_points_and_window():
    seen: dict[str, str] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(dict(req.url.params))
        return httpx.Response(
            200,
            json={
                "hits": [
                    {"title": "New LLM", "points": 200, "objectID": "9", "url": "https://l.example"}
                ]
            },
        )

    (item,) = await HackerNewsSource(transport=httpx.MockTransport(handler)).fetch()
    assert item.score == 200
    assert seen["tags"] == "story" and "points>100" in seen["numericFilters"]
    assert "created_at_i>" in seen["numericFilters"]


@pytest.mark.asyncio
async def test_source_raises_on_http_error():
    source = HackerNewsSource(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(httpx.HTTPStatusError):
        await source.fetch()


# ── 인터랙터 ──────────────────────────────────────────────
class _Source(HotSourcePort):
    def __init__(self, name: str, items: list[HotItem] | Exception) -> None:
        self._name = name
        self._items = items

    @property
    def name(self) -> str:
        return self._name

    async def fetch(self) -> list[HotItem]:
        if isinstance(self._items, Exception):
            raise self._items
        return self._items


def _hot(url: str, score: int, source: str = HOT_COMMUNITY) -> HotItem:
    return HotItem(
        art(url, f"글 {score}", origin="feed", group="community"), source, score, f"{score}점"
    )


@pytest.mark.asyncio
async def test_refresh_saves_articles_and_scores_even_if_a_source_fails():
    repo = FakeRepo()
    await repo.save_articles([art("https://a.example/old", "이미 있는 글", origin="feed")])
    report = await NewsHotInteractor(
        repo,
        [
            _Source(HOT_PAPERS, RuntimeError("503")),
            _Source(
                HOT_COMMUNITY,
                [
                    _hot("https://a.example/old?utm_source=hn", 300),
                    _hot("https://a.example/new", 150),
                ],
            ),
        ],
    ).refresh()

    assert report.fetched == {HOT_COMMUNITY: 2}
    assert len(report.errors) == 1 and HOT_PAPERS in report.errors[0]
    assert len(repo.articles) == 2  # 이미 있던 글은 새로 저장하지 않는다
    assert repo.hot == [
        HotUpdate(1, HOT_COMMUNITY, 300, "300점"),
        HotUpdate(2, HOT_COMMUNITY, 150, "150점"),
    ]


# ── 저장소 (SQLite) ──────────────────────────────────────────
pytest.importorskip("aiosqlite")


@pytest_asyncio.fixture
async def repo():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from news.adapter.outbound.orm.base import NewsBase
    from news.adapter.outbound.pg.news_pg_repository import NewsPgRepository

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(NewsBase.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield NewsPgRepository(session)
    await engine.dispose()


def _a(n: int, section: str, group: str, title: str) -> FetchedArticle:
    return FetchedArticle(
        url=f"https://a.example/{n}",
        title=title,
        summary="요약",
        source_domain="a.example",
        origin="feed",
        published_at=datetime(2026, 11, 5, 9, tzinfo=UTC) + timedelta(minutes=n),
        section=section,
        group=group,
    )


@pytest.mark.asyncio
async def test_repo_hot_ranks_by_source_and_drops_stale(repo):
    a, b, c = await repo.save_articles(
        [
            _a(1, "ai", "paper", "Low paper"),
            _a(2, "ai", "paper", "RAG paper"),
            _a(3, "ai", "community", "HN post"),
        ]
    )
    await repo.set_hot(
        [
            HotUpdate(a.id, HOT_PAPERS, 5, "추천 5"),
            HotUpdate(b.id, HOT_PAPERS, 83, "추천 83"),
            HotUpdate(c.id, HOT_COMMUNITY, 300, "300점 · 댓글 1"),
        ]
    )
    now = datetime.now(UTC)
    rows = await repo.list_hot(HOT_PAPERS, limit=10, since=now - timedelta(hours=1))
    assert [(r.title, r.hot_label) for r in rows] == [
        ("RAG paper", "추천 83"),
        ("Low paper", "추천 5"),
    ]
    assert [
        r.title for r in await repo.list_hot(HOT_PAPERS, limit=1, since=now - timedelta(hours=1))
    ] == ["RAG paper"]
    assert await repo.list_hot(HOT_PAPERS, limit=10, since=now + timedelta(hours=1)) == []

    # 수치를 다시 받으면 새 값으로 바뀐다 — 숫자는 쌓지 않는다
    await repo.set_hot([HotUpdate(a.id, HOT_PAPERS, 90, "추천 90")])
    rows = await repo.list_hot(HOT_PAPERS, limit=10, since=now - timedelta(hours=1))
    assert [r.hot_label for r in rows] == ["추천 90", "추천 83"]

    # 읽기: 출처별로 나뉘고 사전 용어가 붙는다
    hot = await NewsReadInteractor(repo).hot(3)
    assert [r.title for r in hot.papers] == ["Low paper", "RAG paper"]
    assert [r.title for r in hot.community] == ["HN post"]
    assert "RAG" in {t.term.split(" ")[0] for t in hot.papers[1].terms}
    assert HOT_WINDOW_HOURS >= 6


@pytest.mark.asyncio
async def test_pending_puts_hot_first_and_empty_summary_is_done(repo):
    econ, new_ai, hot_old = await repo.save_articles(
        [
            _a(30, "economy", "outlet", "금리"),
            _a(20, "ai", "lab", "New AI post"),
            _a(1, "ai", "community", "Old but hot"),
        ]
    )
    await repo.set_hot([HotUpdate(hot_old.id, HOT_COMMUNITY, 500, "500점")])
    pending = await repo.pending_summaries(limit=10, max_tries=3)
    assert [p.title for p in pending] == ["Old but hot", "New AI post", "금리"]

    # 내용이 없어 제목만 옮긴 글(summary_ko="")은 끝난 글이다 — 다시 요약하지 않는다
    await repo.save_summary(hot_old.id, KoSummary("오래됐지만 화제", ""), "exaone3.5:7.8b")
    assert [p.title for p in await repo.pending_summaries(limit=10, max_tries=3)] == [
        "New AI post",
        "금리",
    ]
    assert econ.id != new_ai.id
