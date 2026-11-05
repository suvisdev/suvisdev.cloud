"""한국어 제목·요약 한 주기 — 수집 뒤에 이어서 돈다(노트북 스케줄러).

영어 글은 제목을 옮기고 요약하고, 한국어 글은 요약만 한다(domain/ko_summary.py). AI 섹션이 먼저다 —
목적이 AI 기술 공부라서(11-05). 모델 서버가 안 되면 그 주기는 바로 멈춘다 — 실패 횟수를 세지 않으니
노트북이 다시 켜지면 그대로 이어진다. 모델 출력이 틀린 글만 실패를 세고 MAX_TRIES 번이면 더 시도하지 않는다.
"""

from __future__ import annotations

import logging

from news.app.dtos.news_dtos import SummaryReport
from news.app.ports.input.news_use_cases import NewsSummarizeUseCase
from news.app.ports.output.news_repository import NewsRepositoryPort
from news.app.ports.output.news_summarizer_port import (
    ArticleSummarizerPort,
    SummarizerUnavailableError,
)

logger = logging.getLogger(__name__)

MAX_TRIES = 3


class NewsSummarizeInteractor(NewsSummarizeUseCase):
    def __init__(self, repository: NewsRepositoryPort, summarizer: ArticleSummarizerPort) -> None:
        self._repository = repository
        self._summarizer = summarizer

    async def summarize_pending(self, limit: int) -> SummaryReport:
        report = SummaryReport(model=self._summarizer.model_name)
        targets = await self._repository.pending_summaries(limit=limit, max_tries=MAX_TRIES)
        for target in targets:
            try:
                result = await self._summarizer.summarize(target)
            except SummarizerUnavailableError as e:
                logger.warning("[news] 요약 모델 응답 없음 — 이번 주기 멈춤: %s", e)
                report.unavailable = True
                break
            if result is None:
                await self._repository.mark_summary_failed(target.id)
                report.failed += 1
                continue
            await self._repository.save_summary(target.id, result, report.model)
            report.done += 1
        return report
