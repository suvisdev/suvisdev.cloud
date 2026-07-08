"""@see suvisdev/_claude/ENTITY_RULE.md — mova 테이블 공통 int PK `id`."""

from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import MovaBase


class MovaModel(MovaBase):
    """모든 mova ORM 테이블의 추상 베이스 — PK: int 자동 증감 `id`."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
