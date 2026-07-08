from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_neo_theone_base import Base


class JackTrainerOrm(Base):
    """JackTrainerCommand → passengers (PK: `passenger_id` str)."""

    __tablename__ = "titanic_passengers"

    passenger_id: Mapped[str] = mapped_column(String(32), primary_key=True, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    gender: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    age: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    sib_sp: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    parch: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    survived: Mapped[str] = mapped_column(String(8), nullable=False, default="")
