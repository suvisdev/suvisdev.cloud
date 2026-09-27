from __future__ import annotations

from pydantic import BaseModel, Field


class PushTokenSchema(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    platform: str = Field(default="android", max_length=16)


class PushTokenDeleteSchema(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class AppVersionSchema(BaseModel):
    platform: str
    min_version: str
    latest_version: str
    store_url: str | None
