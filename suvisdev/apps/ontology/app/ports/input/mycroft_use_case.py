from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.mycroft_dto import MycroftAnswerDto, MycroftAskCommand


class MycroftUseCase(ABC):
    @abstractmethod
    async def ask(self, command: MycroftAskCommand) -> MycroftAnswerDto:
        """게이트웨이 인텐트 분류 결과가 RAG/CRUD가 아닐 때 — Gemini로 범용 응답."""
