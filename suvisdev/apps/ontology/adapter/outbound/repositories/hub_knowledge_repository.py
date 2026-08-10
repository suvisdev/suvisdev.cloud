from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ontology.adapter.outbound.orm.hub_knowledge_orm import HubKnowledgeOrm
from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto, HubKnowledgeUpsertCommand
from ontology.app.ports.output.hub_knowledge_port import HubKnowledgePort


class HubKnowledgeRepository(HubKnowledgePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, command: HubKnowledgeUpsertCommand, embedding: list[float]) -> int:
        """**flush만 하고 commit은 하지 않는다 — 호출자가 커밋해야 한다.**

        FastAPI 경로에선 `get_mova_db()` 의존성이 응답 종료 시 커밋해 주지만,
        일회성 스크립트가 `get_mova_session_factory()`로 세션을 직접 열면
        아무도 커밋하지 않아 **작업이 통째로 사라진다**(2026-08-02 발견).
        같은 저장소의 `MoviesPgRepository.update_*`는 메서드 안에서 커밋하므로
        레포지토리마다 정책이 다르다 — 스크립트를 새로 쓸 땐 쓰는 레포지토리가
        어느 쪽인지 확인할 것. 커밋하는 예: `scripts/ingest_hub_knowledge.py`.
        """
        stmt = (
            insert(HubKnowledgeOrm)
            .values(
                source=command.source,
                source_ref=command.source_ref,
                title=command.title,
                content=command.content,
                embedding=embedding,
            )
            .on_conflict_do_update(
                index_elements=[HubKnowledgeOrm.source_ref],
                set_={
                    "title": command.title,
                    "content": command.content,
                    "embedding": embedding,
                },
            )
            .returning(HubKnowledgeOrm.id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one()

    async def search(
        self, vector: list[float], *, k: int, source: str | None = None
    ) -> list[HubKnowledgeHitDto]:
        distance = HubKnowledgeOrm.embedding.cosine_distance(vector)
        stmt = select(HubKnowledgeOrm, distance.label("distance")).where(
            HubKnowledgeOrm.embedding.is_not(None)
        )
        if source:
            stmt = stmt.where(HubKnowledgeOrm.source == source)
        stmt = stmt.order_by(distance).limit(k)

        rows = (await self._session.execute(stmt)).all()
        return [
            HubKnowledgeHitDto(
                source_ref=row.HubKnowledgeOrm.source_ref,
                title=row.HubKnowledgeOrm.title,
                content=row.HubKnowledgeOrm.content,
                score=1.0 - float(row.distance),
            )
            for row in rows
        ]
