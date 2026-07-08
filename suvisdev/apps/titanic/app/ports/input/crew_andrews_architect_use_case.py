from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from titanic.adapter.inbound.api.schemas.crew_andrews_architect_schema import AndrewsArchitectSchema
from titanic.app.dtos.crew_andrews_architect_dto import AndrewsArchitectResponse


class AndrewsArchitectUseCase(ABC):

    @abstractmethod
    def analyze_intent(self, question: str) -> dict[str, Any]:
        '''Kiwi 형태소 분석으로 프론트 질문의 의도를 파악하는 추상 메소드'''
        pass

    @abstractmethod
    def generate_reply(self, question: str, ml_context: dict) -> str:
        '''ML 예측 결과(ml_context)를 받아 질문에 맞는 응답 문자열을 반환하는 추상 메소드'''
        pass

    @abstractmethod
    async def introduce_myself(self, schema: AndrewsArchitectSchema) -> AndrewsArchitectResponse:
        '''앤드류 아키텍트의 자기소개 메소드'''
        pass
