"""검색 출력 포트 — 검색어로 영화를 찾는 Repository 계약."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_search_dto import SearchResultDto


class SearchRepositoryPort(ABC):
    @abstractmethod
    async def search_by_label(self, q: str, limit: int, offset: int) -> SearchResultDto:
        pass
