"""대화 스레드 PgRepository — ORM 접근."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_conversations_orm import (
    MovaConversation,
    MovaConversationMessage,
)
from mova.app.dtos.market_conversations_dto import (
    ConversationDetailDto,
    ConversationMessageDto,
    ConversationSummaryDto,
)
from mova.app.ports.output.market_conversations_repository import ConversationsRepository


class ConversationsPgRepository(ConversationsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: int) -> list[ConversationSummaryDto]:
        # 메시지 수는 서브쿼리 하나로 뽑는다 — 대화 100개 규모까지는 문제 없음.
        msg_count_subq = (
            select(
                MovaConversationMessage.conversation_id,
                func.count(MovaConversationMessage.id).label("cnt"),
            )
            .group_by(MovaConversationMessage.conversation_id)
            .subquery()
        )
        stmt = (
            select(
                MovaConversation.id,
                MovaConversation.title,
                MovaConversation.updated_at,
                func.coalesce(msg_count_subq.c.cnt, 0).label("cnt"),
            )
            .outerjoin(msg_count_subq, msg_count_subq.c.conversation_id == MovaConversation.id)
            .where(MovaConversation.user_id == user_id)
            .order_by(MovaConversation.updated_at.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ConversationSummaryDto(
                id=row.id, title=row.title, updated_at=row.updated_at, message_count=int(row.cnt)
            )
            for row in rows
        ]

    async def get_owner_id(self, conversation_id: int) -> int | None:
        stmt = select(MovaConversation.user_id).where(MovaConversation.id == conversation_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_detail(self, conversation_id: int) -> ConversationDetailDto | None:
        conv_stmt = select(MovaConversation).where(MovaConversation.id == conversation_id)
        conv = (await self._session.execute(conv_stmt)).scalar_one_or_none()
        if conv is None:
            return None
        msg_stmt = (
            select(MovaConversationMessage)
            .where(MovaConversationMessage.conversation_id == conversation_id)
            .order_by(MovaConversationMessage.id.asc())
        )
        msg_rows = (await self._session.execute(msg_stmt)).scalars().all()
        return ConversationDetailDto(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=[
                ConversationMessageDto(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    meta=m.meta or {},
                    created_at=m.created_at,
                )
                for m in msg_rows
            ],
        )

    async def create(self, user_id: int, title: str) -> int:
        row = MovaConversation(user_id=user_id, title=title[:80] or "새 대화")
        self._session.add(row)
        await self._session.flush()  # id 확보
        await self._session.commit()
        return row.id

    async def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        meta: dict[str, Any],
    ) -> None:
        msg = MovaConversationMessage(
            conversation_id=conversation_id, role=role, content=content, meta=meta
        )
        self._session.add(msg)
        # updated_at 갱신을 트리거하려면 UPDATE를 명시적으로 한 번 쳐야 한다
        # (onupdate=func.now()는 UPDATE 문에만 걸리므로).
        await self._session.execute(
            update(MovaConversation)
            .where(MovaConversation.id == conversation_id)
            .values(updated_at=func.now())
        )
        await self._session.commit()

    async def delete(self, conversation_id: int) -> None:
        conv = await self._session.get(MovaConversation, conversation_id)
        if conv is not None:
            await self._session.delete(conv)
            await self._session.commit()

    async def get_recent_recommendation_slugs(
        self, conversation_id: int, limit: int = 30
    ) -> set[str]:
        stmt = (
            select(MovaConversationMessage.meta)
            .where(
                MovaConversationMessage.conversation_id == conversation_id,
                MovaConversationMessage.role == "assistant",
            )
            .order_by(MovaConversationMessage.id.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        slugs: set[str] = set()
        for meta in rows:
            if not isinstance(meta, dict):
                continue
            recs = meta.get("recommendations")
            if not isinstance(recs, list):
                continue
            for r in recs:
                if isinstance(r, dict):
                    slug = r.get("id")
                    if isinstance(slug, str) and slug:
                        slugs.add(slug)
        return slugs

    async def get_last_evaluation_movie_id(self, conversation_id: int) -> int | None:
        stmt = (
            select(MovaConversationMessage.meta)
            .where(
                MovaConversationMessage.conversation_id == conversation_id,
                MovaConversationMessage.role == "assistant",
            )
            .order_by(MovaConversationMessage.id.desc())
            .limit(1)
        )
        meta = (await self._session.execute(stmt)).scalar_one_or_none()
        if not isinstance(meta, dict):
            return None
        evaluation = meta.get("evaluation")
        if not isinstance(evaluation, dict):
            return None
        movie_id = evaluation.get("movie_id")
        return movie_id if isinstance(movie_id, int) else None
