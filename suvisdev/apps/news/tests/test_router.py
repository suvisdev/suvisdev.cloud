"""라우터 — 공개 읽기는 로그인 없이, 운영자 API 는 관리자만. 응답에 본문이 없는지도 본다."""

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared.security.require_admin import AdminPrincipal, require_admin

from news.adapter.inbound.api import news_router_root
from news.app.dtos.news_dtos import ArticleDto, GroupDto, SectionDto, TopicDto
from news.app.errors import NewsQueryError, TopicNotFoundError
from news.app.ports.input.news_use_cases import NewsReadUseCase
from news.dependencies.news_provider import get_news_read_use_case

_ROW = ArticleDto(
    id=7,
    title="제목",
    url="https://a.example/7",
    summary="요약",
    source_domain="a.example",
    source_name=None,
    published_at=datetime(2026, 11, 5, tzinfo=UTC),
    badge="ai_suspected",
    reasons_ko=["기자 이름이 없음"],
    section="economy",
    group="outlet",
    sort_at=datetime(2026, 11, 5, 0, 30, tzinfo=UTC),
)


class _Read(NewsReadUseCase):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    async def list_sections(self):
        return [SectionDto("ai", "AI 기술", [GroupDto("lab", "연구소·기업 블로그", ["OpenAI"])])]

    async def list_public_topics(self, section=None):
        self.calls.append(("topics", section))
        return [TopicDto(1, "반도체", "반도체", True, True, "economy")]

    async def list_topic_articles(self, topic_id, *, limit, before):
        if topic_id != 1:
            raise TopicNotFoundError(topic_id)
        return [_ROW]

    async def list_latest(self, *, section, group, limit, before):
        self.calls.append(("latest", section, group))
        if group == "bad":
            raise NewsQueryError("없는 묶음")
        return []

    async def search(self, query, *, section, limit, before):
        self.calls.append(("search", query, section))
        return [_ROW]


def _client(read: _Read | None = None, admin: bool = False) -> TestClient:
    app = FastAPI()
    app.include_router(news_router_root, prefix="/api/v1")
    app.dependency_overrides[get_news_read_use_case] = lambda: read or _Read()
    if admin:
        app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="")
    return TestClient(app)


def test_public_endpoints_without_login():
    read = _Read()
    c = _client(read)
    assert c.get("/api/v1/news/topics").json() == [
        {"id": 1, "label": "반도체", "query": "반도체", "section": "economy"}
    ]
    rows = c.get("/api/v1/news/topics/1/articles?limit=5").json()
    assert rows[0]["badge"] == "ai_suspected" and rows[0]["reasons_ko"] == ["기자 이름이 없음"]
    assert rows[0]["section"] == "economy" and rows[0]["group"] == "outlet"
    assert rows[0]["sort_at"].startswith("2026-11-05T00:30")  # 다음 쪽 기준 시각
    assert "body" not in rows[0]  # 본문은 내보내지 않는다
    assert c.get("/api/v1/news/topics/2/articles").status_code == 404
    assert c.get("/api/v1/news/latest").json() == []
    assert ("latest", "ai", None) in read.calls  # 기본 섹션은 AI(메인)
    assert c.get("/api/v1/news/latest?limit=500").status_code == 422


def test_sections_latest_filters_and_search():
    read = _Read()
    c = _client(read)
    (sec,) = c.get("/api/v1/news/sections").json()
    assert sec["code"] == "ai" and sec["groups"][0]["feeds"] == ["OpenAI"]
    assert c.get("/api/v1/news/latest?section=economy&group=outlet").status_code == 200
    assert ("latest", "economy", "outlet") in read.calls
    assert c.get("/api/v1/news/latest?section=sports").status_code == 422
    assert c.get("/api/v1/news/latest?group=bad").status_code == 400
    assert c.get("/api/v1/news/topics?section=economy").status_code == 200
    assert ("topics", "economy") in read.calls

    rows = c.get("/api/v1/news/search", params={"q": "금리 인하", "section": "economy"}).json()
    assert rows[0]["id"] == 7 and ("search", "금리 인하", "economy") in read.calls
    assert c.get("/api/v1/news/search").status_code == 422  # q 필수
    assert c.get("/api/v1/news/search", params={"q": "x" * 51}).status_code == 422


def test_admin_endpoints_require_admin_token():
    c = _client()
    assert c.get("/api/v1/news/admin/topics").status_code == 401
    assert c.post("/api/v1/news/admin/topics", json={"query": "반도체"}).status_code == 401
    assert c.post("/api/v1/news/admin/collect").status_code == 401
