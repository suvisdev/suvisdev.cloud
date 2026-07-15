from __future__ import annotations

from pydantic import BaseModel


class SemanticAskSchema(BaseModel):
    question: str


class SemanticRouteResponseSchema(BaseModel):
    destination: str
    entities: list[str]
    answer: str
