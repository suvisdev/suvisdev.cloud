from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto, HubKnowledgeUpsertCommand


class HubRagUseCase(ABC):
    @abstractmethod
    async def ingest_movie(self, command: HubKnowledgeUpsertCommand) -> bool:
        """Spoke 이벤트(TMDB/KOFIC 임포트 등) → 임베딩 → hub_knowledge upsert.

        반환: True=색인됨, False=임베딩 실패(레이트리밋 등)로 색인 생략.
        실패를 예외로 올리지 않는 것은 의도(임포트 트랜잭션을 막지 않기 위함)지만,
        재시도가 필요한 배치 스크립트는 이 반환값으로 실패를 알 수 있다
        (2026-08-26: 전량 재임베딩에서 2,083건이 조용히 생략된 사고 후 추가).
        """

    @abstractmethod
    async def search_movies(
        self, query: str, *, k: int = 8, trace_id: str = ""
    ) -> list[HubKnowledgeHitDto]:
        """질문 임베딩 → hub_knowledge 코사인 유사도 검색."""
