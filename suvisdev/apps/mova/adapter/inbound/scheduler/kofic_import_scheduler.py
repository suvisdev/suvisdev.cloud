"""KOFIC 일간 박스오피스 자동 수입 스케줄러 — lifespan 백그라운드 루프.

수동 트리거(POST /mova/import/kofic)와 동일한 유스케이스를 24시간 간격으로 호출해
카탈로그를 매일 최신 국내 박스오피스로 자동 보강한다.
"""

from __future__ import annotations

import asyncio
import logging

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.outbound.http.kofic_box_office_adapter import KoficBoxOfficeAdapter
from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter
from mova.adapter.outbound.pg.market_rankings_pg_repository import RankingsPgRepository
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
from mova.app.dtos.market_box_office_dto import KoficImportCommand
from mova.app.use_cases.import_interactor import ImportInteractor
from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
    HubKnowledgeRepository,
)
from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor
from ontology.dependencies.hub_rag_provider import get_hub_embedding_port

logger = logging.getLogger(__name__)

KOFIC_IMPORT_INTERVAL_SECONDS = 24 * 60 * 60  # 24시간


async def _import_once() -> None:
    keymaker = get_keymaker()
    session_factory = get_mova_session_factory()
    async with session_factory() as session:
        interactor = ImportInteractor(
            movies=MoviesPgRepository(session=session),
            catalog=TmdbCatalogAdapter(keymaker.tmdb_api_key),
            rankings=RankingsPgRepository(session=session),
            box_office=KoficBoxOfficeAdapter(keymaker.kofic_api_key),
            hub_rag=HubRagInteractor(
                repository=HubKnowledgeRepository(session=session),
                # EMBEDDING_BACKEND 분기 재사용 — Ollama 하드코딩 시 gemini
                # 환경에서 신작이 hub RAG에 색인되지 못한다(2026-09-11 리뷰).
                embedding=get_hub_embedding_port(),
            ),
        )
        result = await interactor.import_kofic_boxoffice(KoficImportCommand())
    logger.info(
        "[kofic-scheduler] 일간 박스오피스 수입 완료 — imported=%s message=%s",
        result.imported,
        result.message,
    )


async def run_kofic_import_scheduler() -> None:
    """24시간 간격으로 KOFIC 일간 박스오피스를 카탈로그에 반영한다.

    개별 실패로 루프가 죽지 않도록 예외를 잡아 로깅만 하고 다음 주기로 넘어간다.
    앱 종료 시 task.cancel()이 asyncio.sleep에 CancelledError를 던져 루프가 끝난다.
    """
    while True:
        try:
            await _import_once()
        except Exception as e:
            logger.warning("[kofic-scheduler] 일간 박스오피스 수입 실패: %s", e)
        await asyncio.sleep(KOFIC_IMPORT_INTERVAL_SECONDS)
