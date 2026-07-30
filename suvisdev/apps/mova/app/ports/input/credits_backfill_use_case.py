from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.studio_import_dto import CreditsBackfillResultDto


class CreditsBackfillUseCase(ABC):
    @abstractmethod
    async def backfill_credits(self) -> CreditsBackfillResultDto:
        """기존 movies를 순회하며 TMDB credits(cast/crew)로 actors/characters/movie_directors를 채운다.

        일회성 수동 실행 전용 — seed_catalog_if_sparse/부팅 흐름과는 무관하다.
        """
