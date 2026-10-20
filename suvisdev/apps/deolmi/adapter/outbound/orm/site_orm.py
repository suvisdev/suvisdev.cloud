from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from deolmi.adapter.outbound.orm.base import DeolmiBase


class DeolmiSiteOrm(DeolmiBase):
    """고객(사이트)별 키 한 쌍. 비밀 키는 sha256 해시만 둔다."""

    __tablename__ = "deolmi_sites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_key: Mapped[str] = mapped_column(unique=True)
    secret_hash: Mapped[str]
    name: Mapped[str]
    plan: Mapped[str] = mapped_column(server_default="starter")
    # 허용 도메인(콤마 구분). 비면 Origin 검증 생략(개발·데모용 키).
    domains: Mapped[str] = mapped_column(server_default="")
    active: Mapped[bool] = mapped_column(server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
