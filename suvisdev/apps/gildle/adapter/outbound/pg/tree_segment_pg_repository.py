from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from gildle.adapter.outbound.orm.tree_segment_orm import TreeSegmentOrm
from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.domain.entities.tree_segment import TreeSegment


class PgTreeSegmentRepository(TreeSegmentRepository):
    """TreeSegmentRepository의 PostgreSQL 구현체(sync)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def find_all(self) -> list[TreeSegment]:
        session = self._session_factory()
        rows = session.execute(select(TreeSegmentOrm)).scalars().all()
        return [TreeSegment.from_orm(r) for r in rows]

    def save_many(self, segments: list[TreeSegment]) -> None:
        session = self._session_factory()
        session.execute(delete(TreeSegmentOrm))  # 2.0 스타일(레거시 Query API 제거)
        for seg in segments:
            session.add(
                TreeSegmentOrm(
                    road_name=seg.road_name,
                    start_latitude=seg.start.latitude,
                    start_longitude=seg.start.longitude,
                    end_latitude=seg.end.latitude,
                    end_longitude=seg.end.longitude,
                    species=seg.species.value,
                    quantity=seg.quantity,
                    managing_agency=seg.managing_agency,
                )
            )
        session.commit()
