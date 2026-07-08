from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailDto:
    to: str
    subject: str
    body: str


@dataclass
class EmailIntroduceQuery:
    id: int
    name: str


@dataclass
class EmailIntroduceResponse:
    id: int
    name: str
