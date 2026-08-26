"""@see suvisdev/_claude/ENTITY_RULE.md — OAuth 소셜 로그인 연결 (`user_identities`)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from viewer.adapter.outbound.orm.base_orm import ViewerModel


class UserIdentity(ViewerModel):
    """`users` 계정과 OAuth 프로바이더 계정(google/naver/kakao)을 연결한다."""

    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_user_identities_provider_sub"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
