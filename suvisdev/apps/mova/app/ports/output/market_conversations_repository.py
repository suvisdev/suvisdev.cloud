"""대화 스레드 리포지토리 포트 — 스레드·메시지 CRUD."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mova.app.dtos.market_conversations_dto import (
    ConversationDetailDto,
    ConversationSummaryDto,
)


class ConversationsRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[ConversationSummaryDto]:
        """updated_at DESC, 사이드바용."""

    @abstractmethod
    async def get_owner_id(self, conversation_id: int) -> int | None:
        """소유권 검증용 — 없으면 None."""

    @abstractmethod
    async def get_detail(self, conversation_id: int) -> ConversationDetailDto | None:
        """스레드 + 메시지 전체(오래된→최신 순)."""

    @abstractmethod
    async def create(self, user_id: int, title: str) -> int:
        """새 대화 생성 → id 반환."""

    @abstractmethod
    async def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        meta: dict[str, Any],
    ) -> None:
        """메시지 append + 부모 conversation updated_at 갱신."""

    @abstractmethod
    async def delete(self, conversation_id: int) -> None:
        """CASCADE로 메시지도 함께 지워진다."""

    @abstractmethod
    async def get_recent_recommendation_slugs(
        self, conversation_id: int, limit: int = 30
    ) -> set[str]:
        """대화 스레드의 이전 assistant 메시지 meta.recommendations에서
        영화 슬러그(id 필드) 집합을 뽑아 온다.

        "다른 것 추천해줘" 같은 후속 질의에서 이미 소개한 영화를 다시 추천하지
        않도록 후보 필터링에 쓴다. 30건 정도면 실사용 대화에서 충분(한 대화당
        평균 3~5턴 × 3편 ≈ 15편).
        """

    @abstractmethod
    async def get_last_evaluation_movie_id(self, conversation_id: int) -> int | None:
        """스레드 마지막 assistant 메시지가 evaluate 응답이면 그 movie_id.

        평가를 듣고 난 사용자의 긍정 반응("볼래" 등)을 chat_trend 신호로
        기록할 때 어떤 영화에 대한 반응인지 알아내는 용도(2026-08-28 3트랙).
        """
