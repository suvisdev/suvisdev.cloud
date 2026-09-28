"""ChatReplyService(chat_reply.py) 유닛 테스트 — movie_id 기반 grounding.

2026-08-05 이전엔 테스트가 0건이었다(Phase 1 골든셋 실배포 데이터로만 버그
발견). title 문자열 사후 매칭이 동명이인 오귀속("괴물"→The Thing)과 포맷
미매칭("빽 투 더 퓨쳐 (1985)") 두 버그의 공통 원인이었음을
_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md에서 확정하고, movie_id
기반 grounding으로 교체한 뒤 그 재현 시나리오를 회귀 테스트로 고정한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.schemas.market_chat_schema import (  # noqa: E402
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import (  # noqa: E402
    MovaSearchItemSchema,
)
from mova.adapter.outbound.llm.chat_reply import ChatReplyService  # noqa: E402
from mova.app.dtos.studio_movies_dto import MovieDetailDto  # noqa: E402


def _movie(
    *,
    id: int,
    slug: str,
    title: str,
    release_year: int = 2020,
    poster_url: str = "http://poster",
) -> MovieDetailDto:
    return MovieDetailDto(
        id=id,
        slug=slug,
        title=title,
        release_year=release_year,
        rating=7.0,
        poster_url=poster_url,
        platforms=[],
        age_rating=None,
        genres=[],
        collection_id=None,
        actors=[],
        tags=[],
        synopsis=None,
        trailer_key=None,
    )


def _mock_factory(repo_instance: AsyncMock) -> MagicMock:
    """get_mova_session_factory()()가 async context manager를 반환하는 걸 흉내."""
    session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = False
    factory = MagicMock(return_value=cm)
    return factory, repo_instance


class ParseGeminiReplyTests(unittest.TestCase):
    """파싱 단계에서 movie_id 필수 검증(_GeminiPickSchema)."""

    def setUp(self) -> None:
        self.svc = ChatReplyService()

    def test_valid_pick_with_movie_id_parses(self) -> None:
        raw = (
            '{"intro": "추천합니다", "picks": '
            '[{"movie_id": 147, "title": "기생충", "hook": "명작입니다"}]}'
        )
        intro, recs = self.svc.parse_gemini_reply(raw)

        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].movie_id, 147)
        self.assertEqual(recs[0].title, "기생충")

    def test_pick_missing_movie_id_is_dropped_not_crashed(self) -> None:
        """movie_id 없는 pick 하나가 섞여 있어도 전체 응답이 죽지 않고,
        나머지 유효한 pick은 살아남는다(2026-08-04 도미노 실패와 같은 원칙 —
        하나의 결함이 전체를 막지 않는다)."""
        raw = (
            '{"intro": "추천합니다", "picks": ['
            '{"title": "movie_id 없는 항목", "hook": "이건 드롭됨"},'
            '{"movie_id": 147, "title": "기생충", "hook": "명작입니다"}'
            "]}"
        )
        intro, recs = self.svc.parse_gemini_reply(raw)

        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].movie_id, 147)

    def test_non_integer_movie_id_is_dropped(self) -> None:
        raw = (
            '{"intro": "추천합니다", "picks": '
            '[{"movie_id": "알 수 없음", "title": "제목", "hook": "이유"}]}'
        )
        intro, recs = self.svc.parse_gemini_reply(raw)

        self.assertEqual(recs, [])

    def test_stops_at_three_valid_picks(self) -> None:
        raw_items = ",".join(
            f'{{"movie_id": {i}, "title": "영화{i}", "hook": "이유"}}' for i in range(1, 6)
        )
        raw = f'{{"intro": "추천합니다", "picks": [{raw_items}]}}'
        intro, recs = self.svc.parse_gemini_reply(raw)

        self.assertEqual(len(recs), 3)
        self.assertEqual([r.movie_id for r in recs], [1, 2, 3])

    def test_truncated_reply_keeps_complete_picks(self) -> None:
        """생성 한도에서 잘린 응답(후보를 계속 나열하다 끊김)도 완결된 pick은 살린다(2026-09-28 실측)."""
        raw = (
            '{"intro": "좋은 기분을 느낄 수 있는 영화들을 골라보았습니다.", "picks": ['
            '{"movie_id": 6079, "title": "심슨 가족", "hook": "따뜻한 웃음."}, '
            '{"movie_id": 4206, "title": "그날의 분위기", "hook": "작은 행복."}, '
            '{"movie_id": 5006, "title": "굿 포츈", "hook": "새로운 시작."}, '
            '{"movie_id": 2642, "title": "싸이보그지만 괜'
        )
        intro, recs = self.svc.parse_gemini_reply(raw)

        self.assertEqual(intro, "좋은 기분을 느낄 수 있는 영화들을 골라보았습니다.")
        self.assertEqual([r.movie_id for r in recs], [6079, 4206, 5006])

    def test_truncated_before_any_pick_is_still_failure(self) -> None:
        intro, recs = self.svc.parse_gemini_reply(
            '{"intro": "골라볼게요", "picks": [{"movie_id": 60'
        )
        self.assertEqual(recs, [])


class EnrichFromDbTests(unittest.IsolatedAsyncioTestCase):
    """movie_id로 직접 조회 — title 매칭 경로(find_by_title 등) 사용 안 함."""

    async def test_valid_movie_id_grounds_via_find_by_id_only(self) -> None:
        movie = _movie(id=147, slug="tmdb-496243", title="기생충")
        repo = AsyncMock()
        repo.find_by_id.return_value = movie
        factory, _ = _mock_factory(repo)

        rec = MovaChatRecommendationSchema(id="x", movie_id=147, title="기생충", hook="명작")

        with (
            patch(
                "mova.adapter.outbound.llm.chat_reply.get_mova_session_factory",
                return_value=factory,
            ),
            patch(
                "mova.adapter.outbound.llm.chat_reply.MoviesPgRepository",
                return_value=repo,
            ),
        ):
            enriched = await ChatReplyService().enrich_from_db([rec])

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].movie_id, 147)
        self.assertEqual(enriched[0].id, "tmdb-496243")
        repo.find_by_id.assert_awaited_once_with(147)
        repo.find_by_title.assert_not_awaited()
        repo.get_by_slug.assert_not_awaited()

    async def test_movie_id_not_in_db_is_dropped_with_warning(self) -> None:
        """Gemini가 카탈로그에 없는(또는 존재하지 않는) movie_id를 반환하면
        — 프롬프트 위반 — 그 pick만 드롭하고 나머지는 살아남는다."""
        found = _movie(id=1, slug="tmdb-1", title="정상 영화")
        repo = AsyncMock()
        repo.find_by_id.side_effect = lambda movie_id: found if movie_id == 1 else None
        factory, _ = _mock_factory(repo)

        recs = [
            MovaChatRecommendationSchema(id="a", movie_id=99999, title="존재 안 함", hook="x"),
            MovaChatRecommendationSchema(id="b", movie_id=1, title="정상 영화", hook="y"),
        ]

        with (
            patch(
                "mova.adapter.outbound.llm.chat_reply.get_mova_session_factory",
                return_value=factory,
            ),
            patch(
                "mova.adapter.outbound.llm.chat_reply.MoviesPgRepository",
                return_value=repo,
            ),
            self.assertLogs("mova.adapter.outbound.llm.chat_reply", level="WARNING") as log,
        ):
            enriched = await ChatReplyService().enrich_from_db(recs)

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].movie_id, 1)
        self.assertTrue(any("드롭" in msg for msg in log.output))

    async def test_movie_id_valid_in_db_but_not_offered_is_dropped(self) -> None:
        """2026-08-05 골든셋 재실행 중 실측 — Gemini가 title/hook은 자신이
        실제로 의도한 영화(예: 극한직업) 설명 그대로 두고, movie_id만
        카탈로그에 없는 엉뚱한 값(DB엔 실존하는 다른 영화)을 끼워 보낸
        사례. DB 존재 여부만 확인하면 이걸 못 잡는다(캡틴 아메리카가 실존
        하므로 통과해버림) — 반드시 실제로 제시한 카탈로그 id 집합과
        대조해야 한다."""
        wrong_movie = _movie(id=101, slug="tmdb-822119", title="캡틴 아메리카: 브레이브 뉴 월드")
        repo = AsyncMock()
        repo.find_by_id.return_value = wrong_movie  # DB엔 실존 — 존재 검증만으론 못 잡음
        factory, _ = _mock_factory(repo)

        # 카탈로그엔 101이 없었다(실제로 제시한 후보는 다른 id들뿐).
        catalog = [
            MovaSearchItemSchema(
                id="200", title="극한직업", year="2019", rating=8.0, poster="", match_type="keyword"
            ),
        ]
        rec = MovaChatRecommendationSchema(
            id="x", movie_id=101, title="극한직업", hook="쉴 새 없이 터지는 웃음"
        )

        with (
            patch(
                "mova.adapter.outbound.llm.chat_reply.get_mova_session_factory",
                return_value=factory,
            ),
            patch(
                "mova.adapter.outbound.llm.chat_reply.MoviesPgRepository",
                return_value=repo,
            ),
            self.assertLogs("mova.adapter.outbound.llm.chat_reply", level="WARNING") as log,
        ):
            enriched = await ChatReplyService().enrich_from_db([rec], tag_catalog=catalog)

        self.assertEqual(enriched, [])
        repo.find_by_id.assert_not_awaited()  # 카탈로그 검증에서 이미 걸러져 DB 조회조차 안 감
        self.assertTrue(any("제시한 적 없는" in msg for msg in log.output))

    async def test_movie_id_offered_and_in_db_survives_with_db_title(self) -> None:
        """카탈로그에 실제로 제시됐고 DB에도 있으면 정상 grounding — 최종
        title은 Gemini 텍스트가 아니라 DB 값으로 고정(오귀속 시 제목·실제
        영화 불일치 방지 안전망)."""
        movie = _movie(id=200, slug="tmdb-19404", title="극한직업")
        repo = AsyncMock()
        repo.find_by_id.return_value = movie
        factory, _ = _mock_factory(repo)

        catalog = [
            MovaSearchItemSchema(
                id="200", title="극한직업", year="2019", rating=8.0, poster="", match_type="keyword"
            ),
        ]
        rec = MovaChatRecommendationSchema(
            id="x", movie_id=200, title="극한직업(Gemini 표기)", hook="웃음 폭탄"
        )

        with (
            patch(
                "mova.adapter.outbound.llm.chat_reply.get_mova_session_factory",
                return_value=factory,
            ),
            patch(
                "mova.adapter.outbound.llm.chat_reply.MoviesPgRepository",
                return_value=repo,
            ),
        ):
            enriched = await ChatReplyService().enrich_from_db([rec], tag_catalog=catalog)

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].movie_id, 200)
        self.assertEqual(enriched[0].title, "극한직업")  # DB 값으로 덮어써짐


class MatchingRootCauseRegressionTests(unittest.IsolatedAsyncioTestCase):
    """_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md에서 재현한 두 실측
    버그가 movie_id 기반 grounding으로 더 이상 발생하지 않음을 고정한다."""

    async def test_title_collision_no_longer_misattributes(self) -> None:
        """ "괴물" 재현 — DB엔 The Thing(1982)만 있고 Gemini가 실제로는 다른
        영화(movie_id=147, 기생충)를 의도해 정확한 movie_id를 돌려줬다면,
        title 텍스트가 우연히 "괴물"과 겹치더라도(과거엔 find_by_title이
        엉뚱한 The Thing에 연결했을 상황) movie_id만으로 조회하므로 항상
        Gemini가 실제로 지정한 영화가 나온다 — 동명이인 오귀속 자체가
        불가능해진 구조를 검증."""
        the_thing = _movie(id=426, slug="tmdb-1091", title="괴물", release_year=1982)
        parasite = _movie(id=147, slug="tmdb-496243", title="기생충", release_year=2019)
        repo = AsyncMock()
        repo.find_by_id.side_effect = lambda movie_id: {426: the_thing, 147: parasite}.get(movie_id)
        factory, _ = _mock_factory(repo)

        # Gemini가 "송강호 출연 스릴러" 의도로 movie_id=147(기생충)을 정확히
        # 지정했다고 가정 — title 필드에 오타/구어체가 섞여도(과거라면
        # find_by_title이 완전일치 실패 후 다른 경로에서 "괴물"에 우연히
        # 걸릴 수 있었던 상황) movie_id가 유일한 진실 소스이므로 영향 없다.
        rec = MovaChatRecommendationSchema(
            id="x", movie_id=147, title="기생충", hook="송강호 주연 스릴러"
        )

        with (
            patch(
                "mova.adapter.outbound.llm.chat_reply.get_mova_session_factory",
                return_value=factory,
            ),
            patch(
                "mova.adapter.outbound.llm.chat_reply.MoviesPgRepository",
                return_value=repo,
            ),
        ):
            enriched = await ChatReplyService().enrich_from_db([rec])

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].movie_id, 147)
        self.assertNotEqual(enriched[0].movie_id, 426)  # The Thing으로 안 샘
        repo.find_by_title.assert_not_awaited()  # 문자열 매칭 자체가 안 일어남

    async def test_year_suffix_format_no_longer_breaks_matching(self) -> None:
        """ "빽 투 더 퓨쳐 (1985)" 재현 — 과거엔 title에 연도 접미사가 붙으면
        find_by_title 완전일치가 깨져 movie_id=null이 됐다. 이제는 title이
        뭐라고 적혀 있든 movie_id만 맞으면 정상 grounding된다."""
        movie = _movie(id=194, slug="tmdb-105", title="빽 투 더 퓨쳐", release_year=1985)
        repo = AsyncMock()
        repo.find_by_id.return_value = movie
        factory, _ = _mock_factory(repo)

        rec = MovaChatRecommendationSchema(
            id="x",
            movie_id=194,
            title="빽 투 더 퓨쳐 (1985)",  # Gemini가 연도를 덧붙인 실측 케이스
            hook="시간 여행 SF의 고전",
        )

        with (
            patch(
                "mova.adapter.outbound.llm.chat_reply.get_mova_session_factory",
                return_value=factory,
            ),
            patch(
                "mova.adapter.outbound.llm.chat_reply.MoviesPgRepository",
                return_value=repo,
            ),
        ):
            enriched = await ChatReplyService().enrich_from_db([rec])

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].movie_id, 194)
        self.assertEqual(enriched[0].id, "tmdb-105")


if __name__ == "__main__":
    unittest.main()
