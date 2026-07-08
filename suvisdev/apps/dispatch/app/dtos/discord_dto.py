from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscordDto:
    success: bool


@dataclass
class DiscordIntroduceQuery:
    id: int
    name: str


@dataclass
class DiscordIntroduceResponse:
    id: int
    name: str
