"""라우터 — 공개 읽기는 로그인 없이, 운영자 API 는 관리자만. 응답에 본문이 없는지도 본다."""

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared.security.require_admin import AdminPrincipal, require_admin

from news.adapter.inbound.api import news_router_root
from news.app.dtos.news_dtos import ArticleDto, TopicDto
from news.app.errors import TopicNotFoundError
from news.app.ports.input.news_use_cases import NewsReadUseCase
from news.dependencies.news_provider import get_news_read_use_case


class _Read(NewsReadUseCase):
    async def list_public_topics(self):
        return [TopicDto(1, "반도체", "반도체", True, True)]

    async def list_topic_articles(self, topic_id, *, limit, before):
        if topic_id != 1:
            raise TopicNotFoundError(topic_id)
        return [
            ArticleDto(
                id=7,
                title="제목",
                url="https://a.example/7",
                summary="요약",
                source_domain="a.example",
                source_name=None,
                published_at=datetime(2026, 11, 5, tzinfo=UTC),
                badge="ai_suspected",
                reasons_ko=["기자 이름이 없음"],
            )
        ]

    async def list_latest(self, *, limit, before):
        return []


def _client(admin: bool = False) -> TestClient:
    app = FastAPI()
    app.include_router(news_router_root, prefix="/api/v1")
    app.dependency_overrides[get_news_read_use_case] = lambda: _Read()
    if admin:
        app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="")
    return TestClient(app)


def test_public_endpoints_without_login():
    c = _client()
    assert c.get("/api/v1/news/topics").json() == [{"id": 1, "label": "반도체", "query": "반도체"}]
    rows = c.get("/api/v1/news/topics/1/articles?limit=5").json()
    assert rows[0]["badge"] == "ai_suspected" and rows[0]["reasons_ko"] == ["기자 이름이 없음"]
    assert "body" not in rows[0]  # 본문은 내보내지 않는다
    assert c.get("/api/v1/news/topics/2/articles").status_code == 404
    assert c.get("/api/v1/news/latest").json() == []
    assert c.get("/api/v1/news/latest?limit=500").status_code == 422


def test_admin_endpoints_require_admin_token():
    c = _client()
    assert c.get("/api/v1/news/admin/topics").status_code == 401
    assert c.post("/api/v1/news/admin/topics", json={"query": "반도체"}).status_code == 401
    assert c.post("/api/v1/news/admin/collect").status_code == 401
