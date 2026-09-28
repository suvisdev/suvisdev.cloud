from __future__ import annotations

from abc import ABC, abstractmethod


class WalkUnderstandingError(RuntimeError):
    """이해 모델 호출 실패 — 인터랙터가 규칙 이해로 폴백한다."""


class WalkUnderstandingPort(ABC):
    """산책 요청 자연어 → 슬롯 JSON(검증 전). 실패하면 WalkUnderstandingError."""

    @abstractmethod
    def understand(self, text: str) -> dict[str, object]: ...
