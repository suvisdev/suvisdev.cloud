from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_import_dto import CreditsBackfillResultDto


class CreditsBackfillUseCase(ABC):
    @abstractmethod
    async def backfill_credits(
        self, *, limit: int | None = None, dry_run: bool = False
    ) -> CreditsBackfillResultDto:
        """기존 movies를 순회하며 TMDB credits(cast/crew)로 actors/characters/movie_directors를 채운다.

        일회성 수동 실행 전용 — seed_catalog_if_sparse/부팅 흐름과는 무관하다.
        limit: 앞 N편만 처리(시험 실행용). dry_run: TMDB fetch만 하고 DB write는 생략, 로그만 남김.
        """
