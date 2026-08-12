"""대화 스레드 ORM — 로그인 사용자의 mova 채팅 스레드 + 메시지 로그.

기존 `mova.chat` 테이블은 손대지 않는다(검색·의도 분석 로그 성격 유지).
여기 두 테이블은 Claude/Gemini 스타일 사이드바용 스레드 저장이 목적이라
"대화 단위"를 명시적으로 갖는다.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User


class MovaConversation(MovaModel):
    """사용자별 채팅 스레드. title은 첫 user 메시지 앞 40자로 자동 생성."""

    __tablename__ = "chat_conversations"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Viewer users.id (동일 DB FK). 익명 대화는 저장하지 않음.",
    )
    title: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        comment="사이드바 표시명. 첫 user 메시지 앞 40자 잘라 채움(제목이 UI에서 " \
                "길게 표시되면 흐트러지므로 여유 두고 80).",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
        comment="마지막 메시지 추가 시각. 사이드바 정렬 기준.",
    )


class MovaConversationMessage(MovaModel):
    """대화 스레드의 개별 메시지. role=user/assistant 두 종만 저장한다."""

    __tablename__ = "chat_messages"

    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="user | assistant",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="user: {intent_type, refined_query, keywords}. "
                "assistant: {recommendations: [...]}. 스키마는 프런트가 알고 있음.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
