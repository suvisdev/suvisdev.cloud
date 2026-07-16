from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from ontology.app.dtos.scrape_dto import DatasetMeta, ScrapedRecord


class DatasetWriterPort(ABC):
    @abstractmethod
    def write(
        self, records: Iterable[ScrapedRecord], path: Path, *, append: bool = False
    ) -> DatasetMeta:
        """records를 한 건씩 즉시 flush하며 JSONL로 저장한다 (중간에 끊겨도 수집분은 보존).

        append=True면 기존 파일 뒤에 이어 쓴다 (crawl-batch의 날짜별 누적 저장용).
        """
