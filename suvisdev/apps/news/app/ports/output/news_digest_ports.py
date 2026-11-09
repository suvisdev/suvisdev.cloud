from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from news.app.dtos.news_dtos import ArticleDto


class ClassifierUnavailableError(Exception):
    """분류 모델 서버가 꺼졌거나 응답이 너무 느림 — 이번 메일을 보내지 않고 다음 주기에 다시 한다."""


@dataclass(frozen=True)
class ArticleJudgement:
    label: str  # tech·industry·other
    value: int  # 학습 가치 1~5


class ArticleClassifierPort(ABC):
    @abstractmethod
    async def classify(self, article: ArticleDto) -> ArticleJudgement | None:
        """모델 출력이 형식에 안 맞으면 None, 서버 문제면 예외."""


class DigestMailerPort(ABC):
    @abstractmethod
    def send(self, *, subject: str, text: str, html: str) -> None: ...


class DigestLedgerPort(ABC):
    """하루 한 통을 보장하는 기록. 동기 함수 — 인터랙터가 스레드로 넘긴다."""

    @abstractmethod
    def begin(self, day: date) -> bool:
        """보낼 차례면 True. 이미 보냈거나, 다른 파드가 진행 중이거나, 발송 실패가 한도를 넘으면 False."""

    @abstractmethod
    def record_failure(self, day: date) -> None:
        """메일 발송 실패 한 번."""

    @abstractmethod
    def finish(self, day: date) -> None: ...
