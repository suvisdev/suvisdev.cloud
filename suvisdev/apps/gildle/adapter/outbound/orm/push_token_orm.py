from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from gildle.adapter.outbound.orm.base import GildleBase


class PushTokenOrm(GildleBase):
    """FCM 기기 토큰 (2026-09-27). `token`이 유일키 — 같은 기기가 다른 계정으로
    로그인하면 user_id가 바뀐다. walks와 같은 이유로 users FK는 걸지 않는다."""

    __tablename__ = "push_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True)
    token: Mapped[str] = mapped_column(unique=True)
    platform: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
