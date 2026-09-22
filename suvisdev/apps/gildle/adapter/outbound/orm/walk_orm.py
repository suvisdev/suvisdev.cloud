from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Index, desc, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gildle.adapter.outbound.orm.base import GildleBase


class WalkOrm(GildleBase):
    """산책 기록 — 앱이 "다시 열 이유"를 만드는 유일한 상태 (2026-09-22).

    `user_id`에 FK를 걸지 않는 이유: `users`는 다른 앱(auth/mova)의 테이블이고,
    gildle ORM이 그것을 참조하면 앱 경계를 넘는 결합이 생긴다. 소유권 검사는
    유스케이스에서 principal과 비교해 처리한다.

    `path`는 [[위도, 경도], ...] 배열이다. 위치정보이므로 개인정보처리방침
    (`suvis/app/gildle/privacy`)의 보유·삭제 조항과 함께 관리해야 한다.
    """

    __tablename__ = "walks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True)
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime]
    distance_m: Mapped[int]
    duration_s: Mapped[int]
    # 테스트는 sqlite in-memory로 create_all을 하는데 JSONB는 sqlite 방언에 없다
    # (2026-09-22: 그대로 뒀다가 gildle 테스트 31건이 깨졌다). 방언별로 갈라 준다.
    path: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list
    )
    season_mode: Mapped[str]
    avg_shade_score: Mapped[float | None] = mapped_column(default=None)
    memo: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # 목록은 "내 최근 산책"이 기본 조회라 (user_id, started_at desc)로 받는다.
    __table_args__ = (Index("ix_walks_user_started", "user_id", desc("started_at")),)
