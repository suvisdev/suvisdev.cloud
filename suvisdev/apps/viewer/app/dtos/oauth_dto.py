from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class OAuthIdentity:
    provider: str
    provider_user_id: str
    email: str | None
    name: str | None


@dataclass
class SessionPayloadDto:
    user_id: int
    username: str
    token: str


@dataclass
class OAuthCallbackResultDto:
    """콜백 처리 결과 — 기존 연결 계정이면 바로 세션, 신규면 약관 동의가 먼저 필요하다."""

    kind: Literal["session", "consent_required"]
    code: str
