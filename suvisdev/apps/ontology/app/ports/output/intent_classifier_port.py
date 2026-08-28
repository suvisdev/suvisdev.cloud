from __future__ import annotations

from abc import ABC, abstractmethod


class IntentClassifierPort(ABC):
    @abstractmethod
    async def classify(self, question: str) -> tuple[str, list[str]]:
        """질문 → (destination, entities).

        destination: "crud" | "recommend" | "evaluate" | "booking" | "general".
        2026-08-28 확장 — 기존 "rag"(영화 질의 전체)가 recommend(추천)/
        evaluate(특정 작품 평가)/booking(예매·상영관)으로 세분화됐다. 구현체는
        레거시 "rag" 출력을 "recommend"로 정규화해 돌려준다.
        """
