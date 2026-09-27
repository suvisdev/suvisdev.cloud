from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.chat_understanding_dto import ChatUnderstanding


class ChatUnderstandingError(Exception):
    """이해 단계 실패(LLM 불가·형식 오류). 호출자는 기존 결정론 경로로 폴백한다."""


class ChatUnderstandingPort(ABC):
    """발화 + 최근 대화 → 구조화된 이해(의도·작품명·지역·시각·체인·이어받기)."""

    @abstractmethod
    async def understand(
        self, message: str, history: list[dict[str, str]]
    ) -> ChatUnderstanding: ...
