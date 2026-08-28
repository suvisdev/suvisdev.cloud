"""ExternalReviewPort 구현 — TMDB 공식 리뷰 API(evaluate 트랙 전용)."""

from __future__ import annotations

import logging

from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter, TmdbAdapterError
from mova.app.ports.output.external_review_port import ExternalReviewPort

logger = logging.getLogger(__name__)

_REVIEW_MAX_CHARS = 300


class TmdbReviewAdapter(ExternalReviewPort):
    def __init__(self, tmdb: TmdbAdapter) -> None:
        self._tmdb = tmdb

    async def fetch_reviews(self, tmdb_id: int, *, limit: int = 3) -> list[str]:
        try:
            rows = await self._tmdb.fetch_movie_reviews(tmdb_id)
        except TmdbAdapterError as e:
            # 외부 리뷰는 보강 데이터일 뿐 — 실패해도 평가 흐름은 계속.
            logger.warning("[TmdbReviewAdapter] 리뷰 조회 실패 tmdb_id=%d | %s", tmdb_id, e)
            return []
        excerpts = [
            content[:_REVIEW_MAX_CHARS]
            for row in rows
            if (content := str(row.get("content") or "").strip())
        ]
        return excerpts[:limit]
