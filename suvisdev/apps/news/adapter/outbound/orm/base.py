from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class NewsBase(DeclarativeBase):
    """news 앱 ORM 공통 Base — alembic env.py 의 target_metadata 에 등록한다."""
