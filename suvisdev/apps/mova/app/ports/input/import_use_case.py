from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_box_office_dto import KoficImportCommand
from mova.app.dtos.studio_import_dto import (
    MovieImportResultDto,
    StudioImportQuery,
    StudioImportResponse,
    TmdbImportCommand,
)


class ImportUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: StudioImportQuery) -> StudioImportResponse:
        pass

    @abstractmethod
    async def seed_catalog_if_sparse(self) -> MovieImportResultDto:
        """카탈로그가 비어 있으면 TMDB popular로 자동 채움."""

    @abstractmethod
    async def import_tmdb(self, command: TmdbImportCommand) -> MovieImportResultDto:
        """TMDB ID·검색어·popular 페이지 기반 수동 수입."""

    @abstractmethod
    async def import_kofic_boxoffice(self, command: KoficImportCommand) -> MovieImportResultDto:
        """KOFIC 주간 박스오피스 → 카탈로그 매칭·enrich 후 box_office 랭킹 저장."""
