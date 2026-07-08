from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class GildleBase(DeclarativeBase):
    """gildle 앱 ORM 공통 Base.

    모든 gildle 테이블은 이 Base를 상속하며, alembic autogenerate가 한 metadata로
    모든 테이블을 인식할 수 있게 한다.
    """
