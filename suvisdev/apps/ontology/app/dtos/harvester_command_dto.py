"""어드민 화면의 자연어 명령 → 구조화된 수집 파라미터 VO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HarvesterCommand:
    keyword: str
    limit: int
