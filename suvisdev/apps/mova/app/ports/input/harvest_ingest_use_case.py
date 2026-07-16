"""ingest-harvest CLI가 호출하는 Input Port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from mova.app.dtos.harvest_ingest_dto import HarvestIngestResultDto


class HarvestIngestUseCase(ABC):
    @abstractmethod
    async def ingest(self, jsonl_path: Path) -> HarvestIngestResultDto:
        """harvester JSONL을 읽어 mova RAG(hub_knowledge)에 적재하고 결과를 리포트한다."""
