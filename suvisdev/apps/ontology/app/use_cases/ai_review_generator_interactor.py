"""수집된 JSONL 데이터를 영화별로 묶어 Gemini로 리뷰를 생성하는 유스케이스."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from ontology.app.dtos.ai_review_dto import (
    AiReviewBatchReport,
    AiReviewResult,
    MovieMaterial,
)
from ontology.app.ports.output.ai_review_writer_port import AiReviewWriterPort
from ontology.app.ports.output.hub_llm_port import HubLlmPort

logger = logging.getLogger(__name__)

_REVIEW_SYSTEM_PROMPT = (
    "영화 평론가 톤으로 200~300자 리뷰를 작성해. "
    "줄거리 스포일러는 최소화하고 관람 포인트와 평가를 중심으로. "
    "리뷰 본문만 출력하고 제목이나 별점은 붙이지 마."
)

_RATING_SYSTEM_PROMPT = (
    "아래 영화 리뷰와 수집 자료를 종합적으로 분석해서 1.0~5.0 사이 별점을 0.5 단위로 매겨줘. "
    "긍정적 반응(흥행 성공, 호평, 높은 관객수 등)이면 높은 점수, "
    "부정적 반응이면 낮은 점수를 줘. "
    "숫자 하나만 출력해. 예: 4.0"
)

_RATING_RE = re.compile(r"(\d(?:\.\d)?)")


def load_materials_from_jsonl(directory: Path) -> dict[str, MovieMaterial]:
    """crawled/ 디렉터리의 JSONL 파일들을 읽어 영화 제목별로 소스 데이터를 묶는다."""
    buckets: dict[str, dict[str, Any]] = {}

    for jsonl_path in sorted(directory.glob("*.jsonl")):
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            source = record.get("source", "")

            if source == "google_news":
                group_title = record.get("keyword", "").strip()
            else:
                group_title = record.get("title", "").strip()
            if not group_title:
                continue

            key = _normalize_title(group_title)
            if key not in buckets:
                if source == "google_news":
                    display_title = group_title
                else:
                    display_title = record.get("title", group_title).strip()
                buckets[key] = {
                    "title": display_title,
                    "kowiki_sections": {},
                    "kowiki_infobox": {},
                    "kobis_metrics": {},
                    "news_headlines": [],
                }

            b = buckets[key]

            if source == "kowiki":
                if record.get("sections"):
                    b["kowiki_sections"] = record["sections"]
                if record.get("infobox"):
                    b["kowiki_infobox"] = record["infobox"]
            elif source == "kobis":
                if record.get("metrics"):
                    b["kobis_metrics"] = record["metrics"]
            elif source == "google_news":
                headline = record.get("title", "")
                if headline and headline not in b["news_headlines"]:
                    b["news_headlines"].append(headline)

    return {key: MovieMaterial(**b) for key, b in buckets.items()}


def _normalize_title(title: str) -> str:
    """비교용 정규화 — 괄호 부제 제거, 공백 정리."""
    title = re.sub(r"\s*\(영화\)\s*$", "", title)
    return title.strip().lower()


def _build_review_prompt(mat: MovieMaterial) -> str:
    parts = [f"영화 제목: {mat.title}"]
    if mat.kowiki_infobox:
        info_str = ", ".join(f"{k}: {v}" for k, v in mat.kowiki_infobox.items())
        parts.append(f"기본 정보: {info_str}")
    if mat.kowiki_sections.get("줄거리"):
        parts.append(f"줄거리 요약: {mat.kowiki_sections['줄거리'][:300]}")
    if mat.kowiki_sections.get("평가"):
        parts.append(f"평가: {mat.kowiki_sections['평가'][:300]}")
    if mat.kobis_metrics:
        metrics_str = ", ".join(f"{k}: {v}" for k, v in mat.kobis_metrics.items())
        parts.append(f"흥행 지표: {metrics_str}")
    if mat.news_headlines:
        parts.append(f"관련 뉴스: {'; '.join(mat.news_headlines[:5])}")
    return "\n".join(parts)


def _parse_rating(text: str) -> float:
    m = _RATING_RE.search(text)
    if not m:
        return 3.0
    raw = float(m.group(1))
    clamped = max(1.0, min(5.0, raw))
    return round(clamped * 2) / 2


class AiReviewGeneratorInteractor:
    def __init__(
        self,
        *,
        llm: HubLlmPort,
        writer: AiReviewWriterPort,
    ) -> None:
        self._llm = llm
        self._writer = writer

    async def generate_from_directory(self, directory: Path) -> AiReviewBatchReport:
        materials = load_materials_from_jsonl(directory)
        ai_user_id = await self._writer.ensure_ai_reviewer_user()

        total = len(materials)
        matched = 0
        generated = 0
        skipped = 0
        failed = 0
        results: list[AiReviewResult] = []
        errors: list[str] = []

        for mat in materials.values():
            if not mat.kowiki_sections and not mat.kobis_metrics:
                continue

            movie_id = await self._writer.find_movie_id_by_title(mat.title)
            if movie_id is None:
                norm = _normalize_title(mat.title)
                movie_id = await self._writer.find_movie_id_by_title(norm)
            if movie_id is None:
                logger.debug("[AiReview] DB 매칭 실패 | title=%s", mat.title)
                continue

            matched += 1

            if await self._writer.has_ai_review(ai_user_id, movie_id):
                skipped += 1
                continue

            try:
                result = await self._generate_one(mat, ai_user_id, movie_id)
                results.append(result)
                generated += 1
            except Exception as e:  # noqa: BLE001
                msg = f"{mat.title}: {e!s}"
                logger.warning("[AiReview] 생성 실패 | %s", msg)
                errors.append(msg)
                failed += 1

        return AiReviewBatchReport(
            total_materials=total,
            matched_movies=matched,
            generated_reviews=generated,
            skipped_existing=skipped,
            failed=failed,
            results=results,
            errors=errors,
        )

    async def _generate_one(
        self, mat: MovieMaterial, user_id: int, movie_id: int
    ) -> AiReviewResult:
        prompt = _build_review_prompt(mat)

        body = await self._llm.generate(prompt, system=_REVIEW_SYSTEM_PROMPT)

        rating_input = f"[리뷰]\n{body}\n\n[수집 자료]\n{prompt}"
        rating_response = await self._llm.generate(rating_input, system=_RATING_SYSTEM_PROMPT)
        rating = _parse_rating(rating_response)

        review_id = await self._writer.save_review(
            user_id=user_id,
            movie_id=movie_id,
            rating=rating,
            body=body,
        )

        logger.info(
            "[AiReview] 생성 완료 | title=%s movie_id=%d rating=%.1f",
            mat.title,
            movie_id,
            rating,
        )
        return AiReviewResult(
            movie_title=mat.title,
            movie_id=movie_id,
            rating=rating,
            body=body,
            review_id=review_id,
        )
