"""스크랩 세션 상태 전이 — PENDING → RUNNING → DONE|FAILED. 허용 밖 전이는 예외를 던진다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ScrapeSessionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


_ALLOWED_TRANSITIONS: dict[ScrapeSessionStatus, set[ScrapeSessionStatus]] = {
    ScrapeSessionStatus.PENDING: {ScrapeSessionStatus.RUNNING},
    ScrapeSessionStatus.RUNNING: {ScrapeSessionStatus.DONE, ScrapeSessionStatus.FAILED},
    ScrapeSessionStatus.DONE: set(),
    ScrapeSessionStatus.FAILED: set(),
}


@dataclass
class ScrapeSession:
    """단일 CLI 실행의 생명주기를 추적하는 엔티티."""

    status: ScrapeSessionStatus = ScrapeSessionStatus.PENDING
    error: str | None = None

    def start(self) -> None:
        self._transition(ScrapeSessionStatus.RUNNING)

    def finish(self) -> None:
        self._transition(ScrapeSessionStatus.DONE)

    def fail(self, error: str) -> None:
        self.error = error
        self._transition(ScrapeSessionStatus.FAILED)

    def _transition(self, target: ScrapeSessionStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise ValueError(f"허용되지 않는 상태 전이: {self.status} → {target}")
        self.status = target
