from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.semantic_router_dto import SemanticRouteCommand, SemanticRouteDto


class SemanticRouterUseCase(ABC):
    @abstractmethod
    async def route(self, command: SemanticRouteCommand) -> SemanticRouteDto:
        """질문 1건을 crud/rag/general로 분류하고, 해당 갈래의 답변까지 만들어 반환한다."""
