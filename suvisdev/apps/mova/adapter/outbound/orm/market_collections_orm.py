"""@see suvisdev/_claude/ENTITY_RULE.md — 시리즈/컬렉션 그룹화 (`collections`)."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel


class MovaCollection(MovaModel):
    """시리즈·컬렉션 그룹 (예: '다크 나이트 트릴로지'). movies.collection_id FK 참조."""

    __tablename__ = "collections"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
