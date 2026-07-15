from __future__ import annotations

from abc import ABC, abstractmethod


class IntentClassifierPort(ABC):
    @abstractmethod
    async def classify(self, question: str) -> tuple[str, list[str]]:
        """질문 → (destination, entities). destination: "crud" | "rag" | "general"."""
