from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class KeywordSourcePort(ABC):
    """crawl_config.yaml의 keyword_source로 참조되는 동적 키워드 공급원."""

    source_id: ClassVar[str]

    @abstractmethod
    def resolve(self) -> list[str]:
        """배치 시작 시점에 동적 키워드 목록을 반환한다."""
