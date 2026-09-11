from __future__ import annotations

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_neo_theone_base import Base
from dispatch.app.ports.output.embedding_port import EMBEDDING_DIM


def _utcnow_naive() -> datetime:
    """utcnow() 대체(3.12+ deprecated) — tz 없는 DateTime 컬럼용 naive UTC."""
    return datetime.now(UTC).replace(tzinfo=None)


class DispatchReceiveOrm(Base):
    __tablename__ = "dispatch_inbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender: Mapped[str] = mapped_column(Text, nullable=False, default="")
    subject: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow_naive)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
