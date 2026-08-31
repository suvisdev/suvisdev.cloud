"""시맨틱 게이트웨이(질문 1건 → crud/rag/general 세 갈래) DTO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ontology.adapter.inbound.api.schemas.semantic_router_schema import (
        SemanticAskSchema,
        SemanticRouteResponseSchema,
    )


@dataclass(frozen=True)
class SemanticRouteCommand:
    question: str

    @classmethod
    def from_schema(cls, payload: SemanticAskSchema) -> SemanticRouteCommand:
        return cls(question=payload.question)


@dataclass(frozen=True)
class SemanticRouteDto:
    destination: str
    entities: list[str]
    answer: str

    def to_schema(self) -> SemanticRouteResponseSchema:
        from ontology.adapter.inbound.api.schemas.semantic_router_schema import (
            SemanticRouteResponseSchema,
        )

        return SemanticRouteResponseSchema(
            destination=self.destination,
            entities=self.entities,
            answer=self.answer,
        )
