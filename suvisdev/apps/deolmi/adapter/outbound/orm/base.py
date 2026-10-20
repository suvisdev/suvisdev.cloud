from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class DeolmiBase(DeclarativeBase):
    """덜미 앱 ORM 공통 Base. alembic env.py의 target_metadata에 등록돼 있다."""
