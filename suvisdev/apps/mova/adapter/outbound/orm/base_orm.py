"""@see suvisdev/_claude/ENTITY_RULE.md — mova 테이블 공통 int PK `id`."""

from typing import Final

from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import MovaBase

# mova 벡터 컬럼(movies·reviews·user_taste_vectors) 공통 차원. Gemini
# `gemini-embedding-001`을 `output_dimensionality=768`로 잘라 채운다 — hub_knowledge의
# EMBEDDING_DIM(1024, bge-m3)과 다르므로 mova 임베딩 생성 경로는 이 값을 명시해야 한다.
MOVA_EMBEDDING_DIM: Final[int] = 768


class MovaModel(MovaBase):
    """모든 mova ORM 테이블의 추상 베이스 — PK: int 자동 증감 `id`."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
