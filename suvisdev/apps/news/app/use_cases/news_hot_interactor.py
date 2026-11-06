"""오늘의 핫한 소식 갱신 — 화제 출처의 반응 수치를 기사에 적는다. 수집 주기마다 돈다(domain/hot.py).

새 글은 기사로 저장하고(그 뒤 요약 단계가 먼저 처리한다), 이미 있는 글은 수치만 고친다. 한 출처가 실패해도 다른 출처는 계속한다.
"""

from __future__ import annotations

from collections.abc import Sequence

from news.app.dtos.news_dtos import HotReport, HotUpdate
from news.app.ports.input.news_use_cases import NewsHotUseCase
from news.app.ports.output.news_repository import NewsRepositoryPort
from news.app.ports.output.news_source_ports import HotSourcePort
from news.domain.url import canonical_url


class NewsHotInteractor(NewsHotUseCase):
    def __init__(self, repository: NewsRepositoryPort, sources: Sequence[HotSourcePort]) -> None:
        self._repository = repository
        self._sources = list(sources)

    async def refresh(self) -> HotReport:
        report = HotReport()
        for source in self._sources:
            try:
                items = await source.fetch()
            except Exception as e:  # 한 출처 실패가 주기 전체를 멈추지 않게
                report.errors.append(f"화제 출처 실패 {source.name}: {e}")
                continue
            report.fetched[source.name] = len(items)
            if not items:
                continue
            stored = await self._repository.save_articles([i.article for i in items])
            ids = {s.url: s.id for s in stored}
            await self._repository.set_hot(
                [
                    HotUpdate(ids[key], i.source, i.score, i.label)
                    for i in items
                    if (key := canonical_url(i.article.url)) in ids
                ]
            )
        return report
