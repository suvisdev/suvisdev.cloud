from __future__ import annotations

from pydantic import BaseModel


class HarvesterSiteSchema(BaseModel):
    site_id: str
    fetcher_kind: str


class HarvesterCommandRequestSchema(BaseModel):
    site_id: str
    command_text: str


class HarvesterRunResponseSchema(BaseModel):
    record_count: int
    path: str
    parsed_keyword: str
    parsed_limit: int
