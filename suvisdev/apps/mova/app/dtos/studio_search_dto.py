"""검색 DTO."""

from __future__ import annotations

from dataclasses import dataclass

from mova.app.dtos.studio_movies_dto import MovieListItemDto


@dataclass(frozen=True)
class SearchResultDto:
    query: str
    items: list[MovieListItemDto]
    total: int
    limit: int
    offset: int

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_search_schema import SearchResultSchema

        return SearchResultSchema(
            query=self.query,
            items=[item.to_schema() for item in self.items],
            total=self.total,
            limit=self.limit,
            offset=self.offset,
        )
