"""evaluate 트랙 — "호프 어때?" 류 질의에 리뷰·지표 기반 객관 평가를 만든다.

ChatInteractor가 destination=evaluate일 때 위임하는 앱 레이어 서비스.
저장(chat·대화 스레드)은 ChatInteractor 책임으로 남긴다(한 곳 유지).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mova.app.dtos.market_chat_dto import ChatEvaluationDto, ChatRecommendationDto
from mova.app.ports.output.external_review_port import ExternalReviewPort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.review_aggregation_port import ReviewAggregationPort
from mova.app.use_cases.market_chat_title_resolver import resolve_movie_title
from ontology.app.dtos.mycroft_dto import MycroftAskCommand
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase

logger = logging.getLogger(__name__)

# 자체 리뷰가 이보다 적으면 표본 부족을 반드시 명시한다(정직성 규칙).
_SMALL_SAMPLE_THRESHOLD = 3

_EVALUATION_SYSTEM_PROMPT = (
    "너는 mova의 영화 평가 도우미다. 아래 [데이터]만 근거로 해당 작품을 한국어로 "
    "간결하게(4~6문장) 평가한다. 규칙:\n"
    "1) 정량(평점·리뷰 수)과 정성(리뷰 내용 요약)을 구분해 서술한다.\n"
    "2) 데이터에 없는 내용을 지어내지 않는다 — 수상 이력·흥행 성적 등 근거 없는 "
    "사실 언급 금지.\n"
    "3) 자체 리뷰가 표본 부족(임계 미만)으로 표시돼 있으면 '참고용'임을 명시한다.\n"
    "4) 외부(TMDB) 리뷰가 영어면 내용을 한국어로 요약해 반영한다.\n"
    "5) 스포일러(결말·반전)를 언급하지 않는다.\n"
    "6) 마지막 문장은 어떤 취향에게 맞을지 한 줄 제안으로 끝낸다."
)


@dataclass(frozen=True)
class EvaluationResult:
    status: str  # "ok" | "not_found" | "ambiguous"
    reply: str
    card: ChatRecommendationDto | None
    evaluation: ChatEvaluationDto | None


def _tmdb_id_from_slug(slug: str) -> int | None:
    """slug 규칙 `tmdb-{id}`(mova CLAUDE.md §B.5) — TMDB 원산이 아니면 None."""
    if slug.startswith("tmdb-") and slug[5:].isdigit():
        return int(slug[5:])
    return None


class MovieEvaluationService:
    def __init__(
        self,
        *,
        repository: ChatRepositoryPort,
        movies: MoviesRepositoryPort,
        reviews: ReviewAggregationPort,
        general: MycroftUseCase,
        external_reviews: ExternalReviewPort | None = None,
    ) -> None:
        self._repository = repository
        self._movies = movies
        self._reviews = reviews
        self._general = general
        self._external_reviews = external_reviews

    async def evaluate(
        self, *, message: str, entities: list[str], trace_id: str
    ) -> EvaluationResult:
        resolution = await resolve_movie_title(self._repository, message=message, entities=entities)
        if resolution.status == "not_found":
            return EvaluationResult(
                status="not_found",
                reply=(
                    "말씀하신 작품을 저희 카탈로그에서 찾지 못했어요. "
                    "정확한 제목으로 다시 알려주시면 평가해 드릴게요."
                ),
                card=None,
                evaluation=None,
            )
        if resolution.status == "ambiguous":
            names = " / ".join(
                f"{c.title}({c.year})" if c.year else c.title for c in resolution.candidates
            )
            return EvaluationResult(
                status="ambiguous",
                reply=f"비슷한 제목이 여러 편이에요: {names}. 어떤 작품을 말씀하시나요?",
                card=None,
                evaluation=None,
            )

        assert resolution.item is not None
        movie_id = int(resolution.item.id)
        detail = await self._movies.find_by_id(movie_id)
        if detail is None:  # 검색 직후 삭제된 극단 케이스만 — 정직하게 안내
            return EvaluationResult(
                status="not_found",
                reply="작품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
                card=None,
                evaluation=None,
            )

        aggregate = await self._reviews.aggregate_for_movie(movie_id)
        tmdb_id = _tmdb_id_from_slug(detail.slug)
        external: list[str] = []
        if self._external_reviews is not None and tmdb_id is not None:
            external = await self._external_reviews.fetch_reviews(tmdb_id)

        reply = await self._compose_reply(
            title=detail.title,
            year=detail.release_year,
            genres=detail.genres,
            synopsis=detail.synopsis or "",
            tmdb_rating=detail.rating,
            aggregate_count=aggregate.review_count,
            aggregate_avg=aggregate.avg_rating,
            excerpts=aggregate.excerpts,
            external=external,
        )
        logger.info(
            "[MovieEvaluationService] trace=%s movie_id=%d reviews=%d external=%d",
            trace_id,
            movie_id,
            aggregate.review_count,
            len(external),
        )
        platform = detail.platforms[0].provider if detail.platforms else None
        return EvaluationResult(
            status="ok",
            reply=reply,
            card=ChatRecommendationDto(
                id=detail.slug,
                movie_id=movie_id,
                title=detail.title,
                year=str(detail.release_year or ""),
                poster=detail.poster_url or "",
                synopsis=detail.synopsis or "",
                platform=platform,
                hook="리뷰·평점 기반 평가",
            ),
            evaluation=ChatEvaluationDto(
                movie_id=movie_id,
                review_count=aggregate.review_count,
                avg_rating=aggregate.avg_rating,
                tmdb_rating=round(float(detail.rating), 2) if detail.rating else None,
                excerpts=aggregate.excerpts,
            ),
        )

    async def _compose_reply(
        self,
        *,
        title: str,
        year: int,
        genres: list[str],
        synopsis: str,
        tmdb_rating: float,
        aggregate_count: int,
        aggregate_avg: float | None,
        excerpts: list[str],
        external: list[str],
    ) -> str:
        lines = [
            f"[작품] {title} ({year or '연도 미상'}) | 장르: {', '.join(genres) or '미상'}",
            f"[정량] TMDB 유래 평점(5점 만점): {tmdb_rating or '없음'} | "
            f"mova 자체 리뷰: {aggregate_count}건"
            + (f", 평균 {aggregate_avg}점" if aggregate_avg is not None else ""),
        ]
        if aggregate_count < _SMALL_SAMPLE_THRESHOLD:
            lines.append(f"[주의] 자체 리뷰 표본 부족(임계 {_SMALL_SAMPLE_THRESHOLD}건 미만).")
        if synopsis:
            lines.append(f"[시놉시스] {synopsis[:300]}")
        for i, text in enumerate(excerpts, 1):
            lines.append(f"[자체 리뷰 발췌 {i}] {text}")
        for i, text in enumerate(external, 1):
            lines.append(f"[TMDB 리뷰 발췌 {i}] {text}")
        answer = await self._general.ask(
            MycroftAskCommand(
                question="[데이터]\n" + "\n".join(lines),
                system=_EVALUATION_SYSTEM_PROMPT,
            )
        )
        return answer.text
