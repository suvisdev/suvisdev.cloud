from __future__ import annotations

from dataclasses import dataclass


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
