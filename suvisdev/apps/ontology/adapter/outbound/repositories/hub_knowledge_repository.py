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
