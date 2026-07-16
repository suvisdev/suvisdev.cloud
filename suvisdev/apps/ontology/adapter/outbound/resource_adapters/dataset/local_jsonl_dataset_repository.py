"""로컬 파일시스템에 JSONL로 스트리밍 저장하는 DatasetWriterPort 구현체.

레코드 하나가 나올 때마다 즉시 flush한다 — 전체를 리스트로 모았다가 한 번에 쓰지
않는다. Ctrl+C로 중간에 끊겨도(KeyboardInterrupt는 CLI 계층에서 잡는다) 그때까지
수집분은 파일에 그대로 남는다.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from ontology.app.dtos.scrape_dto import DatasetMeta, ScrapedRecord
from ontology.app.ports.output.dataset_writer_port import DatasetWriterPort


class LocalJsonlDatasetRepository(DatasetWriterPort):
    def write(
        self, records: Iterable[ScrapedRecord], path: Path, *, append: bool = False
    ) -> DatasetMeta:
        path.parent.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now(UTC)
        count = 0
        source = ""
        keyword = ""
        mode = "a" if append else "w"
        with path.open(mode, encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record.to_json_dict(), ensure_ascii=False) + "\n")
                f.flush()
                count += 1
                source = record.source
                keyword = record.keyword
        return DatasetMeta(
            path=str(path),
            record_count=count,
            source=source,
            keyword=keyword,
            started_at=started_at,
            finished_at=datetime.now(UTC),
        )
