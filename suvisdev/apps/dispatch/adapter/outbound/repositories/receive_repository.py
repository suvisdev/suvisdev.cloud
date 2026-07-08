from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.adapter.outbound.orm.receive_orm import DispatchReceiveOrm
from dispatch.app.dtos.receive_dto import ReceiveItem, ReceiveSaveCommand
from dispatch.app.ports.output.receive_port import ReceivePort


class ReceiveRepository(ReceivePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, command: ReceiveSaveCommand, embedding: list[float] | None) -> ReceiveItem:
        row = DispatchReceiveOrm(
            sender=command.sender,
            subject=command.subject,
            body=command.body,
            received_at=datetime.utcnow(),
            embedding=embedding,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_item(row)

    async def list_all(self, limit: int) -> list[ReceiveItem]:
        stmt = (
            select(DispatchReceiveOrm).order_by(DispatchReceiveOrm.received_at.desc()).limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_item(row) for row in result.scalars().all()]

    async def delete(self, item_id: int) -> None:
        await self._session.execute(
            delete(DispatchReceiveOrm).where(DispatchReceiveOrm.id == item_id)
        )


def _to_item(row: DispatchReceiveOrm) -> ReceiveItem:
    return ReceiveItem(
        id=row.id,
        sender=row.sender,
        subject=row.subject,
        body=row.body,
        received_at=row.received_at,
    )
