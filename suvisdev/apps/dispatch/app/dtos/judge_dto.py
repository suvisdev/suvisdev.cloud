from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JudgeIntroduceQuery:
    id: int
    name: str


@dataclass(frozen=True)
class JudgeIntroduceResponse:
    id: int
    name: str
