from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmithCaptainQuery:
    id: int
    name: str


@dataclass(frozen=True)
class SmithCaptainResponse:
    id: int
    name: str


@dataclass(frozen=True)
class SmithChatResponse:
    reply: str


@dataclass(frozen=True)
class SmithCaptainChatCommand:
    messages: str
    system_instruction: str | None = None
    model: str | None = "flash"
 