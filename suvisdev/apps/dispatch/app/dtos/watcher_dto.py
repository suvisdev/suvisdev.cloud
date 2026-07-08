from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WatcherIntroduceQuery:
    id: int
    name: str


@dataclass(frozen=True)
class WatcherIntroduceResponse:
    id: int
    name: str
