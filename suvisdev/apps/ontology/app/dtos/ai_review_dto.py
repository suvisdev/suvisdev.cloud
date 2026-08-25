"""AI 리뷰 생성 파이프라인 VO."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MovieMaterial:
    """하나의 영화에 대해 여러 소스에서 수집한 원재료를 묶은 것."""

    title: str
    kowiki_sections: dict[str, str] = field(default_factory=dict)
    kowiki_infobox: dict[str, str] = field(default_factory=dict)
    kobis_metrics: dict[str, float] = field(default_factory=dict)
    news_headlines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AiReviewResult:
    """생성된 AI 리뷰 한 건."""

    movie_title: str
    movie_id: int
    rating: float
    body: str
    review_id: int


@dataclass(frozen=True)
class AiReviewBatchReport:
    """배치 실행 결과 리포트."""

    total_materials: int
    matched_movies: int
    generated_reviews: int
    skipped_existing: int
    failed: int
    results: list[AiReviewResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
