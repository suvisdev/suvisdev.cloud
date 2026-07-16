"""harvester JSONL 산출물 리더 — HarvestReaderPort 구현체.

harvester(ontology) 모듈은 import하지 않는다. JSONL 한 줄의 dict 구조(파일 포맷)만이
계약이다 — ontology.app.dtos.scrape_dto나 ontology.adapter.outbound.scraper.*는
여기서 절대 참조하지 않는다.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from mova.app.dtos.harvest_ingest_dto import HarvestRow
from mova.app.ports.output.harvest_reader_port import HarvestReaderPort


class HarvestJsonlReaderAdapter(HarvestReaderPort):
    def read(self, path: Path) -> Iterator[HarvestRow]:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                yield HarvestRow(
                    source=str(raw.get("source", "")),
                    url=str(raw.get("url", "")),
                    title=str(raw.get("title", "")),
                    content=str(raw.get("content", "")),
                    sections=raw.get("sections"),
                    infobox=raw.get("infobox"),
                    external_ids=raw.get("external_ids"),
                    metrics=raw.get("metrics"),
                )
