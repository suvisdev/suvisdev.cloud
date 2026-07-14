from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto, HubKnowledgeUpsertCommand


class HubRagUseCase(ABC):
    @abstractmethod
    async def ingest_movie(self, command: HubKnowledgeUpsertCommand) -> None:
        """Spoke 이벤트(TMDB/KOFIC 임포트 등) → 임베딩 → hub_knowledge upsert."""

    @abstractmethod
    async def search_movies(
        self, query: str, *, k: int = 8, trace_id: str = ""
    ) -> list[HubKnowledgeHitDto]:
        """질문 임베딩 → hub_knowledge 코사인 유사도 검색."""
