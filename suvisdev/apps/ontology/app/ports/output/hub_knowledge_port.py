from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto, HubKnowledgeUpsertCommand


class HubKnowledgePort(ABC):
    @abstractmethod
    async def upsert(self, command: HubKnowledgeUpsertCommand, embedding: list[float]) -> int:
        """source_ref 기준 insert 또는 update — id 반환."""

    @abstractmethod
    async def search(
        self, vector: list[float], *, k: int, source: str | None = None
    ) -> list[HubKnowledgeHitDto]:
        """코사인 유사도 상위 k건."""
