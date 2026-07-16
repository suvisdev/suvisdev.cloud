"""harvester JSONL → mova RAG(hub_knowledge) 적재 유스케이스.

source별 콘텐츠 매핑:
- kowiki: content(리드 문단) + sections(줄거리/평가/출연/제작)
- tmdb: content(overview) + infobox(감독/출연/장르/개봉일)
- kobis: content(감독/장르/관람등급/상영시간) + metrics(순위/관객수)
- 그 외(google_news 등): content 그대로 — 이미 제목+요약이 결합돼 있다.

movies_repository.find_by_title()로 기존 movies 레코드와 매칭을 시도한다 — movies
스키마에 tmdb_id/kobis_movie_cd 컬럼이 없어 실제 외부 ID 조인은 아니고, 정확 제목
일치 여부를 매칭/미매칭 건수로 리포트만 한다(DB에 새 링크를 저장하지 않음).

중복 적재 방지는 HubRagUseCase.ingest_movie가 위임하는 hub_knowledge.upsert()의
source_ref(=url) 기준 on_conflict_do_update가 그대로 처리한다 — 여기서 별도 dedup을
하지 않는다.
"""

from __future__ import annotations

import logging
from pathlib import Path

from mova.app.dtos.harvest_ingest_dto import HarvestIngestResultDto, HarvestRow
from mova.app.ports.input.harvest_ingest_use_case import HarvestIngestUseCase
from mova.app.ports.output.harvest_reader_port import HarvestReaderPort
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase

logger = logging.getLogger(__name__)

_KOBIS_METRIC_LABELS = {"rank": "순위", "audi_cnt": "일일 관객수", "audi_acc": "누적 관객수"}


def _map_content(row: HarvestRow) -> str:
    if row.source == "kowiki":
        parts = [row.content]
        for heading, body in (row.sections or {}).items():
            parts.append(f"[{heading}]\n{body}")
        return "\n\n".join(p for p in parts if p)
    if row.source == "tmdb":
        parts = [row.content]
        for key, value in (row.infobox or {}).items():
            parts.append(f"{key}: {value}")
        return "\n".join(p for p in parts if p)
    if row.source == "kobis":
        parts = [row.content]
        for metric_key, metric_value in (row.metrics or {}).items():
            label = _KOBIS_METRIC_LABELS.get(metric_key, metric_key)
            parts.append(f"{label}: {metric_value:.0f}")
        return "\n".join(p for p in parts if p)
    return row.content


class HarvestIngestInteractor(HarvestIngestUseCase):
    def __init__(
        self,
        *,
        reader: HarvestReaderPort,
        movies: MoviesRepositoryPort,
        hub_rag: HubRagUseCase,
    ) -> None:
        self._reader = reader
        self._movies = movies
        self._hub_rag = hub_rag

    async def ingest(self, jsonl_path: Path) -> HarvestIngestResultDto:
        total = 0
        ingested = 0
        matched = 0
        unmatched = 0

        for row in self._reader.read(jsonl_path):
            total += 1
            if not row.url or not row.title:
                logger.warning(
                    "[HarvestIngestInteractor] url/title 누락 행 건너뜀 | source=%s", row.source
                )
                continue

            content = _map_content(row)
            await self._hub_rag.ingest_movie(
                HubKnowledgeUpsertCommand(
                    source=row.source,
                    source_ref=row.url,
                    title=row.title,
                    content=content,
                )
            )
            ingested += 1

            movie = await self._movies.find_by_title(row.title)
            if movie:
                matched += 1
            else:
                unmatched += 1

        logger.info(
            "[HarvestIngestInteractor] 완료 | total=%d ingested=%d matched=%d unmatched=%d",
            total,
            ingested,
            matched,
            unmatched,
        )
        return HarvestIngestResultDto(
            total=total, ingested=ingested, matched=matched, unmatched=unmatched
        )
