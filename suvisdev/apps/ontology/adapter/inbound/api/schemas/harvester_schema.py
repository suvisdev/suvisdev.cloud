from __future__ import annotations

from pydantic import BaseModel


class HarvesterSiteSchema(BaseModel):
    site_id: str
    fetcher_kind: str


class HarvesterCommandRequestSchema(BaseModel):
    command_text: str
    site_id: str | None = None  # 등록된 사이트 모드
    url: str | None = None  # 임의 URL 모드 — 있으면 site_id 대신 이쪽을 쓴다


class HarvesterRunResponseSchema(BaseModel):
    record_count: int
    path: str
    parsed_keyword: str
    parsed_limit: int


class HarvesterPolicySchema(BaseModel):
    """크롤링 탭 — crawl_config.yaml 정책 + Redis 마지막 실행 시각 현황판."""

    site_id: str
    keywords: list[str]
    keyword_source: str | None
    interval_minutes: int
    limit_per_keyword: int | None
    last_run_at: str | None
    is_due: bool
