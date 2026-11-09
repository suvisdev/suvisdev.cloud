"""한국어 제목·요약 — 출력 검사 규칙, 인터랙터, 올라마 어댑터(가짜 전송), 저장소(SQLite)."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from news_fakes import FakeRepo, FakeSummarizer

from news.adapter.outbound.llm.ollama_ko_summarizer import (
    OllamaKoSummarizer,
    build_user_prompt,
)
from news.app.dtos.news_dtos import FetchedArticle, SummaryTarget
from news.app.ports.output.news_summarizer_port import SummarizerUnavailableError
from news.app.use_cases.news_summarize_interactor import MAX_TRIES, NewsSummarizeInteractor
from news.domain.ko_summary import KoSummary, is_korean, parse_ko_summary

_EN = "Sparse Mixture of Experts at Scale"


def _target(i: int, title: str = _EN, section: str = "ai") -> SummaryTarget:
    return SummaryTarget(
        id=i,
        title=title,
        summary="We study sparse experts.",
        body="",
        source_name="arXiv",
        section=section,
    )


# ── 출력 검사 ──────────────────────────────────────────────
def test_parse_valid_output_translates_english_title():
    raw = '{"title_ko": "대규모 희소 전문가 혼합", "summary_ko": "연구팀이 희소 전문가 혼합 모델을 확장해 추론 비용을 줄였다."}'
    assert parse_ko_summary(raw, _EN) == KoSummary(
        "대규모 희소 전문가 혼합", "연구팀이 희소 전문가 혼합 모델을 확장해 추론 비용을 줄였다."
    )


def test_parse_keeps_korean_title_and_tolerates_text_around_json():
    original = "문샷 AI, ‘키미 K3.1 프로’ 가중치 공개"
    raw = 'JSON: {"title_ko": "문샷 AI 가중치 공개", "summary_ko": "문샷 AI가 키미 K3.1 프로 가중치를 공개했다는 소식이다."} 끝'
    out = parse_ko_summary(raw, original)
    assert out is not None and out.title_ko == original  # 한국어 원제는 그대로


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        '{"title_ko": "제목"}',  # 요약 없음
        '{"title_ko": "제목", "summary_ko": "짧다"}',  # 너무 짧음
        '{"title_ko": "t", "summary_ko": "This summary has no Korean at all, only English."}',
        '{"title_ko": "제목", "summary_ko": null}',
    ],
)
def test_parse_rejects_bad_output(raw):
    assert parse_ko_summary(raw, _EN) is None


def test_is_korean_with_mixed_names():
    assert is_korean("오픈AI, GPT-6 공개") and not is_korean("v0.40.14") and not is_korean(_EN)


# ── 인터랙터 ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_summarize_saves_counts_failures_and_stops_when_model_down():
    repo = FakeRepo()
    repo.summary_queue = [_target(1), _target(2, "고장 난 출력"), _target(3, "정전"), _target(4)]
    summarizer = FakeSummarizer()
    report = await NewsSummarizeInteractor(repo, summarizer).summarize_pending(limit=10)

    assert report.done == 1 and report.failed == 1 and report.unavailable is True
    assert summarizer.calls == [1, 2, 3]  # 서버 문제에서 멈춤 — 4번은 다음 주기에
    assert repo.summaries[1][1] == "fake-7.8b"
    assert repo.summary_failures == {2: 1}  # 서버 문제(3번)는 실패로 세지 않는다


@pytest.mark.asyncio
async def test_summarize_gives_up_after_max_tries():
    repo = FakeRepo()
    repo.summary_queue = [_target(2, "고장 난 출력")]
    uc = NewsSummarizeInteractor(repo, FakeSummarizer())
    for _ in range(MAX_TRIES + 2):
        await uc.summarize_pending(limit=10)
    assert repo.summary_failures[2] == MAX_TRIES


# ── 올라마 어댑터 (가짜 전송) ──────────────────────────────
@pytest.mark.asyncio
async def test_ollama_adapter_sends_json_request_and_parses():
    seen: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        seen.update(url=str(req.url), model=body["model"], fmt=body["format"])
        content = json.dumps(
            {
                "title_ko": "대규모 희소 전문가 혼합",
                "summary_ko": "희소 전문가 모델을 키워 비용을 줄였다는 연구다.",
            },
            ensure_ascii=False,
        )
        return httpx.Response(200, json={"message": {"content": content}})

    s = OllamaKoSummarizer(
        base_url="http://ollama.test:11434",
        model="exaone3.5:7.8b",
        transport=httpx.MockTransport(handler),
    )
    out = await s.summarize(_target(1))
    assert out is not None and out.title_ko == "대규모 희소 전문가 혼합"
    assert seen == {
        "url": "http://ollama.test:11434/api/chat",
        "model": "exaone3.5:7.8b",
        "fmt": "json",
    }


@pytest.mark.asyncio
async def test_ollama_adapter_raises_unavailable_on_connect_error_and_5xx():
    def down(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=req)

    s = OllamaKoSummarizer(base_url="http://x.test", transport=httpx.MockTransport(down))
    with pytest.raises(SummarizerUnavailableError):
        await s.summarize(_target(1))

    s5 = OllamaKoSummarizer(
        base_url="http://x.test", transport=httpx.MockTransport(lambda r: httpx.Response(503))
    )
    with pytest.raises(SummarizerUnavailableError):
        await s5.summarize(_target(1))


def test_user_prompt_adds_body_once_and_caps_length():
    t = SummaryTarget(
        id=1,
        title="t",
        summary="요약",
        body="본문" * 2000,
        source_name="조선비즈",
        section="economy",
    )
    p = build_user_prompt(t)
    assert p.startswith("제목: t\n출처: 조선비즈\n내용: 요약\n본문") and len(p) < 2000


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


def _a(n: int, section: str, minutes: int, title: str) -> FetchedArticle:
    return FetchedArticle(
        url=f"https://a.example/{n}",
        title=title,
        summary="요약",
        source_domain="a.example",
        origin="feed",
        published_at=datetime(2026, 11, 5, 9, tzinfo=UTC) + timedelta(minutes=minutes),
        section=section,
        group="lab" if section == "ai" else "outlet",
    )


@pytest.mark.asyncio
async def test_repo_pending_order_save_failed_and_search_korean(repo):
    stored = await repo.save_articles(
        [
            _a(1, "economy", 50, "금리 동결"),
            _a(2, "ai", 0, "Old paper"),
            _a(3, "ai", 30, "Sparse Mixture of Experts"),
        ]
    )
    ids = {s.title: s.id for s in stored}
    pending = await repo.pending_summaries(limit=10, max_tries=3)
    assert [p.title for p in pending] == [
        "Sparse Mixture of Experts",
        "Old paper",
        "금리 동결",
    ]  # AI 먼저

    await repo.save_summary(
        ids["Sparse Mixture of Experts"],
        KoSummary("대규모 희소 전문가 혼합", "희소 전문가 혼합 모델을 키운 연구다."),
        "exaone3.5:7.8b",
    )
    for _ in range(3):
        await repo.mark_summary_failed(ids["Old paper"])
    assert [p.title for p in await repo.pending_summaries(limit=10, max_tries=3)] == ["금리 동결"]

    (row,) = await repo.search_articles(["전문가"], section="ai", limit=10, before=None)
    assert row.title_ko == "대규모 희소 전문가 혼합" and row.summary_ko.startswith("희소")
    latest = await repo.list_latest(section="ai", group=None, limit=10, before=None)
    assert {r.title: r.title_ko for r in latest} == {
        "Sparse Mixture of Experts": "대규모 희소 전문가 혼합",
        "Old paper": None,
    }
