"""AI 리뷰 생성 인터랙터 단위 테스트 — fake LLM + fake writer로 정책 검증."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

import asyncio  # noqa: E402

from ontology.app.ports.output.ai_review_writer_port import AiReviewWriterPort  # noqa: E402
from ontology.app.ports.output.hub_llm_port import HubLlmPort  # noqa: E402
from ontology.app.use_cases.ai_review_generator_interactor import (  # noqa: E402
    AiReviewGeneratorInteractor,
    _normalize_title,
    _parse_rating,
    load_materials_from_jsonl,
)


class _FakeLlm(HubLlmPort):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        if system and "별점" in system:
            return "4.0"
        return "테스트 리뷰입니다. 이 영화는 훌륭합니다."


class _FakeWriter(AiReviewWriterPort):
    def __init__(self) -> None:
        self._movies: dict[str, int] = {}
        self._reviews: dict[tuple[int, int], int] = {}
        self._next_review_id = 1
        self.saved: list[dict] = []

    def add_movie(self, title: str, movie_id: int) -> None:
        self._movies[title.lower()] = movie_id

    async def find_movie_id_by_title(self, title: str) -> int | None:
        return self._movies.get(title.lower())

    async def ensure_ai_reviewer_user(self) -> int:
        return 999

    async def has_ai_review(self, user_id: int, movie_id: int) -> bool:
        return (user_id, movie_id) in self._reviews

    async def save_review(self, *, user_id: int, movie_id: int, rating: float, body: str) -> int:
        rid = self._next_review_id
        self._next_review_id += 1
        self._reviews[(user_id, movie_id)] = rid
        self.saved.append(
            {"user_id": user_id, "movie_id": movie_id, "rating": rating, "body": body}
        )
        return rid


def _write_jsonl(directory: Path, filename: str, records: list[dict]) -> None:
    path = directory / filename
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class LoadMaterialsTest(unittest.TestCase):
    def test_groups_by_title_across_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            _write_jsonl(
                d,
                "kowiki_20260820.jsonl",
                [
                    {
                        "source": "kowiki",
                        "title": "오디세이 (영화)",
                        "sections": {"줄거리": "여정을 그린다.", "평가": "호평"},
                        "infobox": {"감독": "놀란"},
                    }
                ],
            )
            _write_jsonl(
                d,
                "kobis_20260820.jsonl",
                [
                    {
                        "source": "kobis",
                        "title": "오디세이",
                        "metrics": {"rank": 1, "audi_cnt": 50000},
                    }
                ],
            )
            _write_jsonl(
                d,
                "google_news_20260820.jsonl",
                [
                    {
                        "source": "google_news",
                        "keyword": "오디세이",
                        "title": "오디세이 흥행 돌풍",
                    }
                ],
            )

            materials = load_materials_from_jsonl(d)

        self.assertIn("오디세이", materials)
        mat = materials["오디세이"]
        self.assertEqual(mat.kowiki_sections["줄거리"], "여정을 그린다.")
        self.assertAlmostEqual(mat.kobis_metrics["rank"], 1.0)
        self.assertEqual(len(mat.news_headlines), 1)

    def test_news_first_file_does_not_pollute_title(self) -> None:
        """google_news 파일이 이름순으로 먼저 읽혀도 제목은 헤드라인이 아닌 keyword여야 한다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            _write_jsonl(
                d,
                "google_news_20260820.jsonl",
                [
                    {
                        "source": "google_news",
                        "keyword": "오디세이",
                        "title": "오디세이 흥행 돌풍",
                    }
                ],
            )
            _write_jsonl(
                d,
                "kowiki_20260821.jsonl",
                [
                    {
                        "source": "kowiki",
                        "title": "오디세이 (영화)",
                        "sections": {"평가": "호평"},
                    }
                ],
            )

            materials = load_materials_from_jsonl(d)

        self.assertEqual(materials["오디세이"].title, "오디세이")


class NormalizeTitleTest(unittest.TestCase):
    def test_strips_movie_suffix(self) -> None:
        self.assertEqual(_normalize_title("오디세이 (영화)"), "오디세이")

    def test_lowercases(self) -> None:
        self.assertEqual(_normalize_title("The Matrix"), "the matrix")


class ParseRatingTest(unittest.TestCase):
    def test_parses_valid(self) -> None:
        self.assertEqual(_parse_rating("4.5"), 4.5)

    def test_clamps_high(self) -> None:
        self.assertEqual(_parse_rating("7.0"), 5.0)

    def test_clamps_low(self) -> None:
        self.assertEqual(_parse_rating("0.5"), 1.0)

    def test_fallback_on_no_match(self) -> None:
        self.assertEqual(_parse_rating("좋은 영화입니다"), 3.0)


class AiReviewGeneratorInteractorTest(unittest.TestCase):
    def test_generates_review_for_matched_movie(self) -> None:
        llm = _FakeLlm()
        writer = _FakeWriter()
        writer.add_movie("오디세이", 42)
        interactor = AiReviewGeneratorInteractor(llm=llm, writer=writer)

        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            _write_jsonl(
                d,
                "kowiki_20260820.jsonl",
                [
                    {
                        "source": "kowiki",
                        "title": "오디세이 (영화)",
                        "sections": {"줄거리": "여정", "평가": "호평"},
                        "infobox": {"감독": "놀란"},
                    }
                ],
            )
            report = asyncio.run(interactor.generate_from_directory(d))

        self.assertEqual(report.generated_reviews, 1)
        self.assertEqual(report.matched_movies, 1)
        self.assertEqual(len(writer.saved), 1)
        self.assertEqual(writer.saved[0]["movie_id"], 42)
        self.assertEqual(writer.saved[0]["rating"], 4.0)

    def test_skips_existing_review(self) -> None:
        llm = _FakeLlm()
        writer = _FakeWriter()
        writer.add_movie("오디세이", 42)
        writer._reviews[(999, 42)] = 1
        interactor = AiReviewGeneratorInteractor(llm=llm, writer=writer)

        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            _write_jsonl(
                d,
                "kowiki_20260820.jsonl",
                [
                    {
                        "source": "kowiki",
                        "title": "오디세이 (영화)",
                        "sections": {"줄거리": "여정", "평가": "호평"},
                        "infobox": {"감독": "놀란"},
                    }
                ],
            )
            report = asyncio.run(interactor.generate_from_directory(d))

        self.assertEqual(report.skipped_existing, 1)
        self.assertEqual(report.generated_reviews, 0)
        self.assertEqual(len(llm.calls), 0)

    def test_unmatched_movie_not_counted_as_generated(self) -> None:
        llm = _FakeLlm()
        writer = _FakeWriter()
        interactor = AiReviewGeneratorInteractor(llm=llm, writer=writer)

        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            _write_jsonl(
                d,
                "kowiki_20260820.jsonl",
                [
                    {
                        "source": "kowiki",
                        "title": "없는영화",
                        "sections": {"줄거리": "없음"},
                        "infobox": {"감독": "없음"},
                    }
                ],
            )
            report = asyncio.run(interactor.generate_from_directory(d))

        self.assertEqual(report.matched_movies, 0)
        self.assertEqual(report.generated_reviews, 0)


if __name__ == "__main__":
    unittest.main()
