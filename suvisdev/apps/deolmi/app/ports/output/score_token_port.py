from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from deolmi.app.dtos.score_dto import ScoreTokenPayload


class ScoreTokenPort(ABC):
    """점수를 담은 서명 토큰 — 위조 차단, 서버가 결과를 저장할 필요가 없다."""

    @abstractmethod
    def issue(self, site_key: str, result: dict[str, Any]) -> str: ...

    @abstractmethod
    def decode(self, token: str) -> ScoreTokenPayload:
        """서명·만료를 확인한다. 실패 시 TokenExpiredError/TokenInvalidError."""

    @abstractmethod
    def consume(self, payload: ScoreTokenPayload) -> None:
        """한 번 쓴 토큰으로 표시한다. 이미 썼으면 TokenReusedError."""
