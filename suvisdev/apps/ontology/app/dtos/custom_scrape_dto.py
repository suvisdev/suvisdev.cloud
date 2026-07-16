"""임의 URL + 자연어 지시 스크랩 전용 VO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedPage:
    title: str
    content: str
