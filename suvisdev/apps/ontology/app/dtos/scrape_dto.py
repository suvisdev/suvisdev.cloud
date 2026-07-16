"""스크래퍼 CLI 파이프라인 VO — 전부 불변(frozen dataclass)이다.

site_id가 SITE_REGISTRY(adapter 계층)에 실제로 등록돼 있는지는 여기서 검증하지 않는다 —
domain이 adapter를 알면 안 되므로(DIP), 그 확인은 CLI 진입점에서 한다. 여기서는 값의
형태(공백 여부)만 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScrapeTarget:
    """CLI --site/--keyword 입력을 검증해 만드는 VO."""

    site_id: str
    keyword: str

    def __post_init__(self) -> None:
        if not self.site_id.strip():
            raise ValueError("사이트 ID는 공백일 수 없습니다.")
        if not self.keyword.strip():
            raise ValueError("키워드는 공백일 수 없습니다.")


@dataclass(frozen=True)
class ScrapedRecord:
    """수집 단건 레코드 — JSONL 한 줄에 대응한다.

    site_id별로 쓰는 optional 필드가 다르다(RSS는 published_at/publisher/summary,
    위키는 sections/infobox). 안 쓰는 필드는 None으로 두면 직렬화 시 생략된다.
    """

    source: str
    keyword: str
    url: str
    title: str
    content: str
    author_hash: str
    scraped_at: datetime
    rating: float | None = None
    published_at: datetime | None = None  # RSS pubDate
    publisher: str | None = None  # RSS 매체명
    summary: str | None = None  # RSS description(요약)
    sections: dict[str, str] | None = None  # 위키 섹션별 본문, 예: {"줄거리": "..."}
    infobox: dict[str, str] | None = None  # 위키 infobox key-value, 예: {"감독": "..."}

    def to_json_dict(self) -> dict[str, object]:
        record: dict[str, object] = {
            "source": self.source,
            "keyword": self.keyword,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author_hash": self.author_hash,
            "scraped_at": self.scraped_at.isoformat(),
        }
        optional: dict[str, object | None] = {
            "rating": self.rating,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "publisher": self.publisher,
            "summary": self.summary,
            "sections": self.sections,
            "infobox": self.infobox,
        }
        record.update({k: v for k, v in optional.items() if v is not None})
        return record


@dataclass(frozen=True)
class DatasetMeta:
    """수집 1회 실행 요약 — CLI 완료 메시지·rich 출력에 쓴다."""

    path: str
    record_count: int
    source: str
    keyword: str
    started_at: datetime
    finished_at: datetime
