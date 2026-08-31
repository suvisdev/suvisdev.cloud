from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OAuthIdentity:
    provider: str
    provider_user_id: str
    email: str | None


class OAuthAdapter(Protocol):
    def build_authorize_url(self, state: str) -> str: ...
    async def exchange_code(self, code: str) -> OAuthIdentity: ...


class OAuthError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code
