from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class OAuthIdentity:
    provider: str
    provider_user_id: str
    email: str | None
    name: str | None
    # 프로바이더가 이메일 소유를 검증했다고 명시적으로 확인해준 경우만 True.
    # False일 때는 이 이메일로 기존 계정에 자동 연결하지 않는다(계정 탈취 방지).
    email_verified: bool = False


@dataclass
class SessionPayloadDto:
    user_id: int
    username: str
    nickname: str
    token: str
    role: str


@dataclass
class OAuthCallbackResultDto:
    """콜백 처리 결과 — 기존 연결 계정이면 바로 세션, 신규면 약관 동의가 먼저 필요하다."""

    kind: Literal["session", "consent_required"]
    code: str
