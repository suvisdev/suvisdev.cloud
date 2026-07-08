from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramDto:
    success: bool


@dataclass
class TelegramIntroduceQuery:
    id: int
    name: str


@dataclass
class TelegramIntroduceResponse:
    id: int
    name: str
