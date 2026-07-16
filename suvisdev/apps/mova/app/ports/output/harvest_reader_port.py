"""harvester JSONL 산출물 리더 Output Port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from mova.app.dtos.harvest_ingest_dto import HarvestRow


class HarvestReaderPort(ABC):
    @abstractmethod
    def read(self, path: Path) -> Iterator[HarvestRow]:
        """JSONL 파일을 한 줄씩 HarvestRow로 파싱해 순회한다."""
