from __future__ import annotations

import os
from functools import cache

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from deolmi.adapter.outbound.memory.sliding_window_velocity_adapter import (
    SlidingWindowVelocityAdapter,
)
from deolmi.adapter.outbound.ml.isolation_forest_model_adapter import IsolationForestModelAdapter
from deolmi.adapter.outbound.repositories.event_pg_repository import EventPgRepository
from deolmi.adapter.outbound.repositories.site_pg_repository import SitePgRepository
from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.ports.input.score_use_case import ScoreUseCase
from deolmi.app.ports.input.site_admin_use_case import SiteAdminUseCase
from deolmi.app.use_cases.score_interactor import ScoreInteractor
from deolmi.app.use_cases.site_admin_interactor import SiteAdminInteractor

# 모델·토큰(jti 기록)·속도 창은 프로세스에 하나씩만 있어야 한다 — 요청마다 만들면
# 재사용 차단과 폭주 측정이 매번 초기화된다. 모델은 첫 요청 때 학습(수 초)한다;
# 이 provider들은 동기 함수라 FastAPI가 스레드풀에서 돌려 이벤트 루프를 막지 않는다.


@cache
def _model() -> IsolationForestModelAdapter:
    return IsolationForestModelAdapter()


@cache
def _velocity() -> SlidingWindowVelocityAdapter:
    return SlidingWindowVelocityAdapter(window_s=10.0)


@cache
def _tokens_for(secret: str) -> JwtScoreTokenAdapter:
    return JwtScoreTokenAdapter(secret)


def _tokens() -> JwtScoreTokenAdapter:
    secret = os.getenv("DEOLMI_TOKEN_SECRET", "")
    if not secret:
        # 기본값으로 서명하지 않는다(auth 규칙) — 설정 전에는 닫힌 채로 503.
        raise HTTPException(status_code=503, detail="deolmi not configured")
    return _tokens_for(secret)


def get_score_use_case(db: AsyncSession = Depends(get_db)) -> ScoreUseCase:
    return ScoreInteractor(
        sites=SitePgRepository(session=db),
        events=EventPgRepository(session=db),
        model=_model(),
        tokens=_tokens(),
        velocity=_velocity(),
    )


def get_site_admin_use_case(db: AsyncSession = Depends(get_db)) -> SiteAdminUseCase:
    return SiteAdminInteractor(
        sites=SitePgRepository(session=db),
        events=EventPgRepository(session=db),
        model=_model(),
    )
