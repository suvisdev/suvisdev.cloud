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
