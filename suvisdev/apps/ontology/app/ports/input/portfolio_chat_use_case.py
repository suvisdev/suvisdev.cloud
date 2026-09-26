from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.portfolio_chat_dto import PortfolioChatAnswerDto, PortfolioChatCommand


class PortfolioChatUseCase(ABC):
    @abstractmethod
    async def chat(self, command: PortfolioChatCommand) -> PortfolioChatAnswerDto:
        """공개 문서(hub_knowledge source='portfolio_doc')를 근거로 질문에 답한다."""
