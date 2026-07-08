from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalterQuery:
    id: int
    name: str


@dataclass
class WalterResponse:
    id: int
    name: str
