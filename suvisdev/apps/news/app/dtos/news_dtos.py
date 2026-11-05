"""news 앱 Command·Dto. 수집 원천(검색 API·RSS)이 달라도 같은 FetchedArticle 로 모은다.

섹션(section)은 ai(메인) · economy(부록), 묶음(group)은 domain/sections.py 의 GROUPS 코드다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from news.domain.sections import DEFAULT_SECTION, section_of_group


@dataclass(frozen=True)
class FetchedArticle:
    """검색 API·RSS 에서 받은 기사 1건 (저장 전). body 는 RSS 가 직접 준 본문만 — 원문 페이지는 가져오지 않는다."""

    url: str
    title: str
    summary: str
    source_domain: str
    origin: str  # "search" | "feed"
    published_at: datetime | None = None
    source_name: str | None = None
    link: str | None = None  # 검색 API 의 네이버 링크 등 원문 주소와 다른 경우
    body: str = ""
    author: str = ""  # RSS 작성자 필드 — 본문에 기자명이 없을 때 NO_BYLINE 오탐을 막는다
    section: str = DEFAULT_SECTION
    group: str = ""


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    group: str
    max_items: int = 50  # 피드가 보관본 전체를 주는 곳(OpenAI 1,359건 등)이 있어 최신 N건만

    @property
    def section(self) -> str:
        return section_of_group(self.group)


@dataclass(frozen=True)
class TopicDto:
    id: int
    query: str
    label: str
    is_public: bool
    active: bool
    section: str = DEFAULT_SECTION


@dataclass(frozen=True)
class TopicCreateCommand:
    query: str
    label: str
    is_public: bool = True
    section: str = DEFAULT_SECTION


@dataclass(frozen=True)
class TopicUpdateCommand:
    topic_id: int
    label: str | None = None
    is_public: bool | None = None
    active: bool | None = None


@dataclass(frozen=True)
class StoredArticle:
    """저장된 기사 id 와 판정 입력에 필요한 값."""

    id: int
    url: str
    title: str
    summary: str
    body: str
    source_domain: str
    source_name: str | None
    author: str
    is_new: bool
    section: str = DEFAULT_SECTION
    group: str = ""


@dataclass(frozen=True)
class VerdictCommand:
    article_id: int
    layer: str  # "rules" | "llm"
    harness_version: str
    verdict: str  # "normal" | "pending" | "ai"
    badge: str  # "none" | "ai_disclosed" | "ai_suspected"
    reasons_ko: list[str]
    signals: list[dict[str, Any]]


@dataclass(frozen=True)
class ArticleDto:
    """화면에 내보내는 기사. 본문은 담지 않는다 (제목·요약·원문 링크만)."""

    id: int
    title: str
    url: str
    summary: str
    source_domain: str
    source_name: str | None
    published_at: datetime | None
    badge: str
    reasons_ko: list[str]
    section: str = DEFAULT_SECTION
    group: str = ""


@dataclass(frozen=True)
class GroupDto:
    code: str
    label: str
    feeds: list[str]


@dataclass(frozen=True)
class SectionDto:
    code: str
    label: str
    groups: list[GroupDto]


@dataclass
class CollectReport:
    topics: int = 0
    feeds: int = 0
    fetched: int = 0
    irrelevant: int = 0
    new_articles: int = 0
    judged: int = 0
    not_judged: int = 0  # 판정 범위 밖(영어·1차 출처 묶음)이라 규칙 판정을 하지 않은 기사
    verdicts: dict[str, int] = field(default_factory=lambda: {"normal": 0, "pending": 0, "ai": 0})
    errors: list[str] = field(default_factory=list)
