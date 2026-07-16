"""--no-dedup일 때 쓰는 VisitedStorePort — 아무것도 방문한 적 없다고 항상 답한다."""

from __future__ import annotations

from ontology.app.ports.output.visited_store_port import VisitedStorePort


class NoOpVisitedStoreAdapter(VisitedStorePort):
    def is_visited(self, keyword: str, url: str) -> bool:
        return False

    def mark(self, keyword: str, url: str) -> None:
        return None
