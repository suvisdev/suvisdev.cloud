from __future__ import annotations

import os
from functools import cache

import redis
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db, get_mova_session_factory
from deolmi.adapter.outbound.kvstore.redis_velocity_adapter import RedisVelocityAdapter
from deolmi.adapter.outbound.ml.isolation_forest_model_adapter import IsolationForestModelAdapter
from deolmi.adapter.outbound.repositories.event_pg_repository import (
    EventPgLogWriter,
    EventPgRepository,
)
from deolmi.adapter.outbound.repositories.site_pg_repository import (
    SitePgLookup,
    SitePgRepository,
)
from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.ports.input.score_use_case import ScoreUseCase
from deolmi.app.ports.input.site_admin_use_case import SiteAdminUseCase
from deolmi.app.use_cases.score_interactor import ScoreInteractor
from deolmi.app.use_cases.site_admin_interactor import SiteAdminInteractor

# 모델·Redis 클라이언트는 프로세스에 하나씩만 둔다. 모델은 첫 요청 때 학습(수 초)한다;
# 이 provider들은 동기 함수라 FastAPI가 스레드풀에서 돌려 이벤트 루프를 막지 않는다.
# 토큰 jti 기록·속도 창은 Redis(REDIS_URL)에 있다 — 노트북↔집컴 서빙 전환·재시작에도 이어진다.


@cache
def _model() -> IsolationForestModelAdapter:
    return IsolationForestModelAdapter()


@cache
def _redis() -> redis.Redis:
    # from_url은 접속하지 않는다(첫 명령 때 연결). 장애 때 요청이 오래 매달리지 않게 1초 제한.
    return redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_timeout=1.0,
        socket_connect_timeout=1.0,
    )


@cache
def _velocity() -> RedisVelocityAdapter:
    return RedisVelocityAdapter(_redis(), window_s=10)


@cache
def _tokens_for(secret: str) -> JwtScoreTokenAdapter:
    return JwtScoreTokenAdapter(secret, _redis())


def _tokens() -> JwtScoreTokenAdapter:
    secret = os.getenv("DEOLMI_TOKEN_SECRET", "")
    if not secret:
        # 기본값으로 서명하지 않는다(auth 규칙) — 설정 전에는 닫힌 채로 503.
        raise HTTPException(status_code=503, detail="deolmi not configured")
    return _tokens_for(secret)


def get_score_use_case() -> ScoreUseCase:
    # 요청 세션(get_db)을 쓰지 않는다 — 요청 세션은 응답 뒤 로그 기록이 끝날 때까지 연결을 쥐고,
    # 그 로그가 같은 풀에서 연결을 또 기다려 동시 요청이 풀을 채우면 서로 막힌다.
    # 조회·로그가 각자 짧게 빌리고 바로 돌려준다(SitePgLookup·EventPgLogWriter).
    try:
        factory = get_mova_session_factory()
    except RuntimeError as e:  # get_db와 같게: DB 미설정이면 503
        raise HTTPException(status_code=503, detail=str(e)) from e
    return ScoreInteractor(
        sites=SitePgLookup(factory),
        events=EventPgLogWriter(factory),
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
