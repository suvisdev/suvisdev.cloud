"""채팅 3트랙(2026-08-28) — 제목 확정·evaluate/booking 서비스·ChatInteractor 위임."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.schemas.market_chat_schema import (  # noqa: E402
    MovaChatRequest,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import (  # noqa: E402
    MovaSearchItemSchema,
)
from mova.adapter.outbound.http.kofic_adapter import KoficAdapterError  # noqa: E402
from mova.app.dtos.market_chat_dto import ReviewAggregateDto  # noqa: E402
from mova.app.dtos.studio_movies_dto import MovieDetailDto, PlatformDto  # noqa: E402
from mova.app.dtos.user_preference_dto import UserPreferenceDto  # noqa: E402
from mova.app.use_cases.market_chat_booking_interactor import (  # noqa: E402
    _DISCOVERY_PATTERN,
    REGION_ASK_MARKER,
    BookingAssistService,
    _extract_region_signal,
    pending_title_from_history,
)
from mova.app.use_cases.market_chat_evaluation_interactor import (  # noqa: E402
    MovieEvaluationService,
)
from mova.app.use_cases.market_chat_interactor import (  # noqa: E402
    _GENERAL_CHAT_SYSTEM_PROMPT,
    ChatInteractor,
    _is_bare_eval_followup,
    _is_booking_lexicon,
    _is_synopsis_request,
    pick_from_choice_list,
)
from mova.app.use_cases.market_chat_title_resolver import (  # noqa: E402
    resolve_movie_title,
)
from ontology.app.agent.agent_loop import AgentDecision  # noqa: E402
from ontology.app.dtos.mycroft_dto import MycroftAnswerDto  # noqa: E402


def _item(movie_id: int, title: str, year: str = "2021") -> MovaSearchItemSchema:
    return MovaSearchItemSchema(
        id=str(movie_id), title=title, year=year, rating=4.0, poster="", match_type="title"
    )


def _detail(movie_id: int, title: str, *, platforms: list[PlatformDto] | None = None):
    return MovieDetailDto(
        id=movie_id,
        slug=f"tmdb-{movie_id}",
        title=title,
        release_year=2021,
        rating=4.2,
        poster_url="https://img/p.jpg",
        platforms=platforms or [],
        age_rating=None,
        genres=["드라마"],
        collection_id=None,
        actors=[],
        tags=[],
        synopsis="시놉시스",
        trailer_key=None,
    )


class TitleResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_match_wins(self) -> None:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(2, "호프집 사람들"), _item(1, "호프")]
        res = await resolve_movie_title(repo, message="호프 어때??", entities=["호프"])
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.item.title, "호프")

    async def test_trailing_track_words_stripped(self) -> None:
        """entities가 비어도 발화 꼬리("예매하고 싶어")를 떼고 제목을 찾는다."""
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(1, "호프")]
        res = await resolve_movie_title(repo, message="호프 예매하고 싶어", entities=[])
        self.assertEqual(res.status, "ok")
        terms = repo.search_movies_by_title.await_args.args[0]
        self.assertIn("호프", terms)

    async def test_multiple_partial_matches_are_ambiguous(self) -> None:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(2, "호프집"), _item(3, "뉴 호프")]
        res = await resolve_movie_title(repo, message="호프 어때", entities=["호프"])
        self.assertEqual(res.status, "ambiguous")
        self.assertEqual(len(res.candidates), 2)

    async def test_no_match_is_not_found(self) -> None:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = []
        repo.fuzzy_search_movies_by_title.return_value = []
        res = await resolve_movie_title(repo, message="없는영화 어때", entities=[])
        self.assertEqual(res.status, "not_found")

    async def test_particle_stripped_from_title(self) -> None:
        """'더문은 쩸 쓰나' → 조사 '은' 제거 → '더문'이 검색어에 포함."""
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(10, "더 문")]
        await resolve_movie_title(repo, message="더문은 쩸 쓰나", entities=["더문은 쩸 쓰나"])
        terms = repo.search_movies_by_title.await_args.args[0]
        self.assertIn("더문", terms)

    async def test_particle_stripped_ga(self) -> None:
        """'인셉션이 재밌어' → 조사 '이' 제거 → '인셉션'."""
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(11, "인셉션")]
        await resolve_movie_title(repo, message="인셉션이 재밌어", entities=[])
        terms = repo.search_movies_by_title.await_args.args[0]
        self.assertTrue(any("인셉션" in t for t in terms))


class TitleResolverLeadingCandidateTests(unittest.IsolatedAsyncioTestCase):
    """2026-09-27 실사용: "파과 예매할 수 있게 시간봐줘 그럼"이 스파이더맨 후보로 되물었다."""

    async def test_leading_word_is_tried_when_tail_rule_fails(self) -> None:
        repo = AsyncMock()

        async def search(terms, limit):
            return [_item(2315, "파과", "2025")] if "파과" in terms else []

        repo.search_movies_by_title.side_effect = search
        res = await resolve_movie_title(
            repo, message="파과 예매할 수 있게 시간봐줘 그럼", entities=[]
        )
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.item.title, "파과")

    async def test_mid_sentence_exact_word_beats_fuzzy(self) -> None:
        """ "군자에서 인턴 오늘 몇 시에 볼 수 있어?" — 앞 어절 '군자'가 퍼지로 군체·감자를
        끌어오기 전에, 어절 '인턴'의 정확 일치를 잡는다(2026-09-27 라이브)."""
        repo = AsyncMock()
        calls: list[list[str]] = []

        async def search(terms, limit):
            calls.append(list(terms))
            return [_item(1019, "인턴", "2015")] if "인턴" in terms else []

        repo.search_movies_by_title.side_effect = search
        repo.fuzzy_search_movies_by_title.return_value = [_item(7, "군체", "2026")]
        res = await resolve_movie_title(
            repo, message="군자에서 인턴 오늘 몇 시에 볼 수 있어?", entities=[]
        )
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.item.title, "인턴")
        repo.fuzzy_search_movies_by_title.assert_not_awaited()

    async def test_single_char_entity_is_dropped(self) -> None:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = []
        repo.fuzzy_search_movies_by_title.return_value = []
        await resolve_movie_title(repo, message="파과 시간봐줘 그럼", entities=["파"])
        terms = repo.search_movies_by_title.await_args.args[0]
        self.assertNotIn("파", terms)
        self.assertIn("파과", terms)

    async def test_leading_stopword_not_a_candidate(self) -> None:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = []
        repo.fuzzy_search_movies_by_title.return_value = []
        await resolve_movie_title(repo, message="지금 인턴 시간봐줘", entities=[])
        terms = repo.search_movies_by_title.await_args.args[0]
        self.assertNotIn("지금", terms)


class BookingLexiconGuardTests(unittest.TestCase):
    def test_showtime_words_route_to_booking(self) -> None:
        for m in (
            "인턴 영화 시간표 보여줘",
            "호프 상영 시간 알려줘",
            "파과 예매할 수 있게",
            "영화관 어디야",
            "군자에 롯데시네마가 있어?",
            "군자에서 인턴 오늘 몇 시에 볼 수 있어?",
            "군자역 근처에 어느 체인 지점이 있는지 알려줘",
            "인턴 어디서 볼 수 있어?",
        ):
            self.assertTrue(_is_booking_lexicon(m), m)

    def test_recommend_and_plain_chat_are_not_booking(self) -> None:
        for m in (
            "영화관에서 볼만한 거 추천해줘",
            "안녕",
            "인턴 줄거리 알려줘",
            "군자",
            "몇 시간짜리 영화야?",
        ):
            self.assertFalse(_is_booking_lexicon(m), m)

    def test_general_prompt_forbids_realtime_facts_and_points_to_booking(self) -> None:
        self.assertIn("시간표", _GENERAL_CHAT_SYSTEM_PROMPT)
        self.assertIn("지어내지", _GENERAL_CHAT_SYSTEM_PROMPT)
        # "모른다"로 끝내지 않고 예매 도우미(극장 검색·롯데 시간표)로 넘기는 안내가 있어야 한다.
        self.assertIn("롯데시네마", _GENERAL_CHAT_SYSTEM_PROMPT)
        self.assertIn("찾아드린다", _GENERAL_CHAT_SYSTEM_PROMPT)


class BareEvalFollowupDetectorTests(unittest.TestCase):
    """제목 없는 evaluate 후속 판별 — 제목이 남으면 제외해야 한다."""

    def test_bare_triggers_detected(self) -> None:
        for msg in (
            "어떠냐고",
            "어때",
            "어때?",
            "그거 어때",
            "그 영화 어때",
            "평가해줘",
            "리뷰 어때?",
        ):
            self.assertTrue(_is_bare_eval_followup(msg), msg)

    def test_title_bearing_or_unrelated_excluded(self) -> None:
        for msg in (
            "어벤져스 어때",
            "스파이더맨은 어때",
            "좀비 영화 추천해줘",
            "안녕",
            "브랜드 뉴 데이",
        ):
            self.assertFalse(_is_bare_eval_followup(msg), msg)


class SynopsisRequestDetectorTests(unittest.TestCase):
    """제목 있는 줄거리 요청 판별 — 추천 어휘가 섞이면 추천 요청이다."""

    def test_synopsis_words_detected(self) -> None:
        for msg in (
            "기생충 줄거리 알려줘",
            "옵세션 줄거리",
            "인턴 시놉시스 좀",
            "듄 무슨 내용이야",
        ):
            self.assertTrue(_is_synopsis_request(msg), msg)

    def test_recommend_or_unrelated_excluded(self) -> None:
        for msg in ("줄거리 반전 있는 영화 추천해줘", "기생충 어때", "좀비 영화 추천", "안녕"):
            self.assertFalse(_is_synopsis_request(msg), msg)


class MovieEvaluationServiceTests(unittest.IsolatedAsyncioTestCase):
    def _service(self, *, review_count: int = 5) -> tuple[MovieEvaluationService, AsyncMock]:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(7, "호프")]
        movies = AsyncMock()
        movies.find_by_id.return_value = _detail(7, "호프")
        reviews = AsyncMock()
        reviews.aggregate_for_movie.return_value = ReviewAggregateDto(
            review_count=review_count, avg_rating=4.5, excerpts=["연출이 좋다"]
        )
        external = AsyncMock()
        external.fetch_reviews.return_value = ["Great movie"]
        general = AsyncMock()
        general.ask.return_value = MycroftAnswerDto(text="객관 평가 텍스트")
        service = MovieEvaluationService(
            repository=repo,
            movies=movies,
            reviews=reviews,
            general=general,
            external_reviews=external,
        )
        return service, general

    async def test_llm_failure_degrades_to_quantitative_summary(self) -> None:
        """Gemini 503이 HubRagError로 올라와도 500이 아니라 정량 요약 200으로 강등된다
        (2026-09-22 멀티턴 "26년꺼" 장면 실측)."""
        from ontology.app.ports.output.hub_rag_errors import HubRagError

        service, general = self._service()
        general.ask.side_effect = HubRagError("503 UNAVAILABLE", status_code=502)
        result = await service.evaluate(message="호프 어때??", entities=["호프"], trace_id="t")

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.card.movie_id, 7)
        self.assertIn("호프", result.reply)
        self.assertIn("리뷰 5건", result.reply)
        self.assertNotIn("TMDB", result.reply)
        self.assertIn("혼잡", result.reply)

    async def test_ok_builds_card_and_payload(self) -> None:
        service, general = self._service()
        result = await service.evaluate(message="호프 어때??", entities=["호프"], trace_id="t")

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.reply, "객관 평가 텍스트")
        self.assertEqual(result.card.movie_id, 7)
        self.assertEqual(result.evaluation.review_count, 5)
        question = general.ask.await_args.args[0].question
        self.assertIn("[mova 리뷰 1]", question)
        self.assertIn("[관객 리뷰 1]", question)
        self.assertNotIn("TMDB", question)  # 평점은 mova 기준만(2026-09-28)
        self.assertNotIn("표본 부족", question)

    async def test_small_sample_is_flagged_in_prompt(self) -> None:
        """정직성 규칙 — 리뷰 3건 미만이면 표본 부족을 LLM 입력에 명시한다."""
        service, general = self._service(review_count=1)
        await service.evaluate(message="호프 어때??", entities=["호프"], trace_id="t")
        self.assertIn("표본 부족", general.ask.await_args.args[0].question)

    async def test_not_found_returns_honest_reply(self) -> None:
        service, _ = self._service()
        service._repository.search_movies_by_title.return_value = []
        service._repository.fuzzy_search_movies_by_title.return_value = []
        result = await service.evaluate(message="없는영화 어때", entities=[], trace_id="t")
        self.assertEqual(result.status, "not_found")
        self.assertIsNone(result.card)

    async def test_ambiguous_returns_structured_candidates(self) -> None:
        """모호하면 후보를 prose뿐 아니라 구조화(candidates)해 준다 — 프론트 선택 칩용."""
        service, _ = self._service()
        service._repository.search_movies_by_title.return_value = [
            _item(1, "스파이더맨: 노 웨이 홈", "2021"),
            _item(2, "스파이더맨: 브랜드 뉴 데이", "2026"),
        ]
        result = await service.evaluate(
            message="스파이더맨 어때", entities=["스파이더맨"], trace_id="t"
        )
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(
            [c.title for c in result.candidates],
            ["스파이더맨: 노 웨이 홈", "스파이더맨: 브랜드 뉴 데이"],
        )
        self.assertEqual(result.candidates[0].slug, "1")

    async def test_no_data_movie_gets_honest_reply_without_llm(self) -> None:
        """줄거리·평점·리뷰가 전무하면(미개봉 신작 등) 지어내지 않고 자료 부족을 알린다."""
        service, general = self._service(review_count=0)
        no_data = MovieDetailDto(
            id=7,
            slug="tmdb-7",
            title="브랜드 뉴 데이",
            release_year=2026,
            rating=0.0,
            poster_url="",
            platforms=[],
            age_rating=None,
            genres=[],
            collection_id=None,
            actors=[],
            tags=[],
            synopsis="",
            trailer_key=None,
        )
        service._movies.find_by_id.return_value = no_data
        service._external_reviews.fetch_reviews.return_value = []
        service._reviews.aggregate_for_movie.return_value = ReviewAggregateDto(
            review_count=0, avg_rating=None, excerpts=[]
        )
        result = await service.evaluate(message="어때", entities=["브랜드 뉴 데이"], trace_id="t")
        self.assertEqual(result.status, "ok")
        self.assertIn("자료가 부족", result.reply)
        general.ask.assert_not_awaited()  # 근거 없는 hype를 LLM에 맡기지 않는다


class BookingAssistServiceTests(unittest.IsolatedAsyncioTestCase):
    def _service(self, *, showing: bool = True) -> BookingAssistService:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(7, "호프")]
        movies = AsyncMock()
        movies.find_by_id.return_value = _detail(
            7, "호프", platforms=[PlatformDto(provider="Netflix", url=None, type=None)]
        )
        box_office = AsyncMock()
        entry = AsyncMock()
        entry.title = "호프" if showing else "다른 영화"
        box_office.fetch_box_office.return_value = [entry]
        theaters = AsyncMock()
        return BookingAssistService(
            repository=repo, movies=movies, box_office=box_office, theaters=theaters
        )

    async def test_duplicate_title_prefers_box_office_year(self) -> None:
        """인턴(2015)·인턴(2026) 중 예매는 상영 중인 2026년작이어야 한다(2026-09-27 사용자 지적)."""
        from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto

        service = self._service()
        service._repository.search_movies_by_title.return_value = [
            _item(1019, "인턴", "2015"),
            _item(4715, "인턴", "2026"),
        ]
        service._movies.find_by_id.return_value = _detail(4715, "인턴")
        service._box_office.fetch_box_office.return_value = [
            BoxOfficeEntryDto(rank=2, movie_cd="x", title="인턴", open_year=2026)
        ]
        result = await service.assist(message="인턴 예매하고 싶어", entities=["인턴"], trace_id="t")
        self.assertEqual(result.status, "ok")
        service._movies.find_by_id.assert_awaited_with(4715)

    async def test_showing_titles_lists_box_office_with_year(self) -> None:
        from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto

        service = self._service()
        service._box_office.fetch_box_office.return_value = [
            BoxOfficeEntryDto(rank=1, movie_cd="a", title="오디세이", open_year=2026),
            BoxOfficeEntryDto(rank=2, movie_cd="b", title="인턴"),
        ]
        self.assertEqual(await service.showing_titles(), ["오디세이(2026)", "인턴"])

    async def test_showing_asks_region_with_marker(self) -> None:
        service = self._service(showing=True)
        result = await service.assist(message="호프 예매하고 싶어", entities=["호프"], trace_id="t")

        self.assertEqual(result.booking.status, "need_region")
        self.assertIn(REGION_ASK_MARKER, result.reply)
        self.assertIn("『호프』", result.reply)
        self.assertEqual(result.resolved_movie_id, 7)

    async def test_not_showing_mentions_ott(self) -> None:
        service = self._service(showing=False)
        result = await service.assist(message="호프 예매하고 싶어", entities=["호프"], trace_id="t")

        self.assertEqual(result.booking.status, "not_showing")
        self.assertIn("넷플릭스", result.reply)
        # 상영 안 하면 볼 수 있는 곳을 링크로(2026-09-28) — OTT 검색 + TMDB 시청처
        chains = [link.chain for link in result.booking.watch_links]
        self.assertEqual(chains[0], "넷플릭스")
        self.assertIn("netflix.com/search?q=", result.booking.watch_links[0].url)

    async def test_region_continuation_lists_theaters(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service(showing=True)
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(name="CGV 강남", address="서울", distance_m=300, place_url="", phone="")
        ]
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(result.booking.status, "showing")
        self.assertEqual(result.booking.region, "강남")
        self.assertEqual(len(result.booking.theaters), 1)
        self.assertTrue(result.booking.booking_links)
        self.assertIn("CGV 강남", result.reply)

    async def test_pending_title_parsed_from_history(self) -> None:
        history = [
            {"role": "user", "content": "호프 예매하고 싶어"},
            {
                "role": "assistant",
                "content": f"『호프』 상영관을 찾아드릴게요. {REGION_ASK_MARKER}?",
            },
        ]
        self.assertEqual(pending_title_from_history(history), "호프")
        self.assertIsNone(pending_title_from_history([{"role": "assistant", "content": "안녕"}]))


class BookingRegionFirstTests(unittest.IsolatedAsyncioTestCase):
    """지역-선행 이어받기(2026-09-11 실사용 — 옵세션 평가 직후 "군자쪽에 예매할
    시간 있는지"가 지명 퍼지 매칭돼 군체/구원자/감자로 되묻던 오류).

    제목이 발화에서 확정되지 않고 지명 신호(쪽/역/근처)가 있으면, 직전
    assistant 응답에서 영화를 역조회해 곧장 지역 검색으로 잇는다."""

    _HISTORY = [
        {"role": "user", "content": "옵세션 어때?"},
        {
            "role": "assistant",
            "content": "영화 '옵세션'은 사랑이 집착으로 변해가는 과정을 그린 공포물입니다.",
        },
    ]

    def _service(self) -> BookingAssistService:
        repo = AsyncMock()

        async def _search(terms: list[str], limit: int) -> list[MovaSearchItemSchema]:
            # "옵세션"으로 재해석된 뒤에만 정확 일치 — 지명("군자쪽…")은 0건
            if any("옵세션" in t for t in terms):
                return [_item(7, "옵세션", "2026")]
            return []

        repo.search_movies_by_title.side_effect = _search
        # 지명이 퍼지 폴백까지 가면 무관 후보가 나오던 상황 재현
        repo.fuzzy_search_movies_by_title.return_value = [
            _item(1, "군체", "2026"),
            _item(2, "구원자", "2025"),
            _item(3, "감자", "1987"),
        ]
        repo.find_movie_titled_in_text.return_value = _item(7, "옵세션", "2026")
        movies = AsyncMock()
        movies.find_by_id.return_value = _detail(7, "옵세션")
        theaters = AsyncMock()
        theaters.search_theaters.return_value = []
        return BookingAssistService(
            repository=repo, movies=movies, box_office=AsyncMock(), theaters=theaters
        )

    async def test_region_first_uses_context_movie(self) -> None:
        service = self._service()
        result = await service.assist(
            message="군자쪽에 예매할 시간 있는지 확인해줘",
            entities=[],
            trace_id="t",
            history=self._HISTORY,
        )

        # 지명 퍼지 후보 되묻기("군체/구원자/감자")가 아니라 옵세션×군자 검색
        self.assertNotIn("군체", result.reply)
        self.assertEqual(result.booking.region, "군자")
        service._repository.find_movie_titled_in_text.assert_awaited_once()
        service._theaters.search_theaters.assert_awaited_once()

    async def test_region_first_falls_back_to_user_turn_when_reply_has_no_title(self) -> None:
        """평가 응답은 줄거리만 담고 제목이 없다(2026-09-22 실사용 "음반점 직원 베어가…").
        그 응답을 부른 user 발화("옵세션 어때")에서 맥락 영화를 찾는다."""
        service = self._service()

        async def _titled(text: str) -> MovaSearchItemSchema | None:
            return _item(7, "옵세션", "2026") if "옵세션" in text else None

        service._repository.find_movie_titled_in_text.side_effect = _titled
        history = [
            {"role": "user", "content": "옵세션 어때"},
            {
                "role": "assistant",
                "content": "음반점 직원 베어가 소원을 빈 뒤 벌어지는 공포 이야기입니다.",
            },
        ]
        result = await service.assist(
            message="군자쪽에 예매할 시간 있는지 확인해줘",
            entities=[],
            trace_id="t",
            history=history,
        )

        self.assertEqual(result.booking.region, "군자")
        self.assertNotIn("제목을 알려주시겠어요", result.reply)
        self.assertEqual(service._repository.find_movie_titled_in_text.await_count, 2)

    async def test_region_first_without_context_asks_title(self) -> None:
        service = self._service()
        service._repository.find_movie_titled_in_text.return_value = None
        result = await service.assist(
            message="군자쪽에 예매할 시간 있는지 확인해줘",
            entities=[],
            trace_id="t",
            history=self._HISTORY,
        )

        self.assertEqual(result.status, "not_found")
        self.assertIn("군자", result.reply)
        self.assertIn("제목", result.reply)
        self.assertNotIn("군체", result.reply)

    async def test_explicit_title_still_wins_over_region_signal(self) -> None:
        """발화에 제목이 확정되면 지역-선행 경로를 타지 않는다."""
        service = self._service()
        result = await service.assist(
            message="옵세션 예매하고 싶어", entities=["옵세션"], trace_id="t", history=self._HISTORY
        )

        self.assertEqual(result.resolved_movie_id, 7)
        service._repository.find_movie_titled_in_text.assert_not_awaited()

    def test_region_signal_extraction(self) -> None:
        cases = {
            "군자쪽에 예매할 시간 있는지 확인해줘": "군자",
            "강남역에서 볼래": "강남",
            "홍대 근처 상영관": "홍대",
            "저쪽에서 볼래": None,  # 대명사 '저쪽'은 지명 아님
            "호프 예매하고 싶어": None,
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(_extract_region_signal(message), expected)


class BookingDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    """제목 없는 탐색형 예매 질의("뭐 있어")는 title resolver 대신 박스오피스
    상영작 목록으로 답한다(2026-09-02 실사용 — "영화"가 제목 퍼지 매칭돼
    무관 후보로 되묻던 오류)."""

    def _service(
        self, *, titles: list[str] | None = None, kofic_error: bool = False
    ) -> tuple[BookingAssistService, AsyncMock]:
        repo = AsyncMock()
        box_office = AsyncMock()
        if kofic_error:
            box_office.fetch_box_office.side_effect = KoficAdapterError("down")
        else:
            entries = []
            for t in titles or []:
                entry = AsyncMock()
                entry.title = t
                entries.append(entry)
            box_office.fetch_box_office.return_value = entries
        service = BookingAssistService(
            repository=repo, movies=AsyncMock(), box_office=box_office, theaters=AsyncMock()
        )
        return service, repo

    async def test_discovery_query_lists_box_office_without_title_resolution(self) -> None:
        service, repo = self._service(titles=["귀멸의 칼날", "F1 더 무비"])
        result = await service.assist(
            message="지금 바로 예매할 수 있는 영화 뭐있어", entities=["영화"], trace_id="t"
        )

        self.assertEqual(result.status, "ok")
        self.assertIn("박스오피스", result.reply)
        self.assertIn("귀멸의 칼날", result.reply)
        self.assertIsNone(result.card)
        self.assertIsNone(result.booking)
        repo.search_movies_by_title.assert_not_awaited()

    async def test_discovery_kofic_failure_gets_honest_fallback(self) -> None:
        service, repo = self._service(kofic_error=True)
        result = await service.assist(message="상영 중인 영화 뭐 있어?", entities=[], trace_id="t")

        self.assertIn("불러오지 못했어요", result.reply)
        repo.search_movies_by_title.assert_not_awaited()

    async def test_title_queries_do_not_match_discovery_pattern(self) -> None:
        """제목 지정 질의는 탐색 패턴에 안 걸려 기존 title 경로가 유지된다."""
        self.assertIsNone(_DISCOVERY_PATTERN.search("호프 예매하고 싶어"))
        self.assertIsNone(_DISCOVERY_PATTERN.search("인셉션 어디서 상영해?"))
        self.assertIsNotNone(_DISCOVERY_PATTERN.search("지금 바로 예매할 수 있는 영화 뭐있어"))
        self.assertIsNotNone(_DISCOVERY_PATTERN.search("요즘 상영작 알려줘"))
        # 2026-09-22 실사용: '뭐있어'가 없어도 '예매할 수 있는 영화'는 탐색형이다
        self.assertIsNotNone(_DISCOVERY_PATTERN.search("바로 예매할 수 있는 영화 찾아줘"))
        self.assertIsNone(_DISCOVERY_PATTERN.search("호프 예매할 수 있는 영화관 알려줘"))


class ChatInteractorTrackDelegationTests(unittest.IsolatedAsyncioTestCase):
    def _interactor(
        self, *, destination: str
    ) -> tuple[ChatInteractor, AsyncMock, AsyncMock, AsyncMock]:
        repo = AsyncMock()
        repo.save_chat.return_value = 11
        repo.find_movie_titled_in_text.return_value = None
        classifier = AsyncMock()
        classifier.classify.return_value = (destination, ["호프"])
        evaluation = AsyncMock()
        booking = AsyncMock()
        interactor = ChatInteractor(
            repository=repo,
            recommender=AsyncMock(),
            preferences=AsyncMock(),
            hub_rag=AsyncMock(),
            classifier=classifier,
            general=AsyncMock(),
            evaluation=evaluation,
            booking=booking,
        )
        return interactor, repo, evaluation, booking

    async def test_evaluate_destination_delegates_and_sets_response_type(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatEvaluationDto, ChatRecommendationDto
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        interactor, repo, evaluation, _ = self._interactor(destination="evaluate")
        evaluation.evaluate.return_value = EvaluationResult(
            status="ok",
            reply="평가",
            card=ChatRecommendationDto(
                id="tmdb-7",
                movie_id=7,
                title="호프",
                year="2021",
                poster="",
                synopsis="",
                platform=None,
                hook="",
            ),
            evaluation=ChatEvaluationDto(
                movie_id=7, review_count=5, avg_rating=4.5, tmdb_rating=4.2, excerpts=[]
            ),
        )

        response = await interactor.chat(MovaChatRequest(message="호프 어때??", history=[]))

        self.assertEqual(response.response_type, "evaluation")
        self.assertEqual(response.intent_type, "evaluate")
        self.assertEqual(len(response.recommendations), 1)
        save_kwargs = repo.save_chat.await_args.kwargs
        self.assertEqual(save_kwargs["intent_type"], "evaluate")
        self.assertEqual(save_kwargs["reply"], "평가")  # 응답 본문도 학습 자료로 남긴다

    async def test_bare_eval_followup_evaluates_movie_from_history(self) -> None:
        """제목 없는 '어떠냐고' 후속은 분류기가 recommend로 오분류해도, 직전 assistant가
        소개한 영화를 역조회해 evaluate로 잇는다(2026-09-09 맥락 이음 수정)."""
        from mova.app.dtos.market_chat_dto import ChatEvaluationDto, ChatRecommendationDto
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        interactor, _, evaluation, _ = self._interactor(destination="recommend")
        interactor._repo.find_movie_titled_in_text.return_value = _item(
            7, "스파이더맨: 브랜드 뉴 데이", "2026"
        )
        evaluation.evaluate.return_value = EvaluationResult(
            status="ok",
            reply="평가",
            card=ChatRecommendationDto(
                id="tmdb-7",
                movie_id=7,
                title="스파이더맨: 브랜드 뉴 데이",
                year="2026",
                poster="",
                synopsis="",
                platform=None,
                hook="",
            ),
            evaluation=ChatEvaluationDto(
                movie_id=7, review_count=0, avg_rating=None, tmdb_rating=3.6, excerpts=[]
            ),
        )
        history = [
            {"role": "user", "content": "브랜드 뉴 데이"},
            {
                "role": "assistant",
                "content": "요청하신 작품을 찾았습니다. 스파이더맨: 브랜드 뉴 데이는 독특합니다.",
            },
        ]
        response = await interactor.chat(MovaChatRequest(message="어떠냐고", history=history))

        self.assertEqual(response.response_type, "evaluation")
        self.assertEqual(
            evaluation.evaluate.await_args.kwargs["entities"], ["스파이더맨: 브랜드 뉴 데이"]
        )

    async def test_titled_synopsis_request_routes_to_evaluate(self) -> None:
        """ "기생충 줄거리 알려줘"는 분류기가 recommend로 오분류해도 카탈로그 제목이 있으면
        evaluate(시놉시스 선행)로 간다. 제목이 없으면 분류기 결과를 따른다."""
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        interactor, repo, evaluation, _ = self._interactor(destination="recommend")
        repo.find_movie_titled_in_text.return_value = _item(9, "기생충", "2019")
        evaluation.evaluate.return_value = EvaluationResult(
            status="not_found", reply="자료 없음", card=None, evaluation=None
        )

        response = await interactor.chat(
            MovaChatRequest(message="기생충 줄거리 알려줘", history=[])
        )

        self.assertEqual(response.intent_type, "evaluate")
        self.assertEqual(evaluation.evaluate.await_args.kwargs["entities"], ["기생충"])
        interactor._classifier.classify.assert_not_awaited()

        interactor2, repo2, evaluation2, _ = self._interactor(destination="general")
        repo2.find_movie_titled_in_text.return_value = None
        await interactor2.chat(MovaChatRequest(message="없는영화 줄거리 알려줘", history=[]))
        evaluation2.evaluate.assert_not_awaited()
        interactor2._classifier.classify.assert_awaited_once()

    async def test_ambiguous_evaluate_carries_choices_to_schema(self) -> None:
        """evaluate 모호 응답의 candidates가 응답 DTO·스키마 choices까지 전달된다."""
        from mova.app.dtos.market_chat_dto import ChatChoiceDto
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        interactor, _, evaluation, _ = self._interactor(destination="evaluate")
        evaluation.evaluate.return_value = EvaluationResult(
            status="ambiguous",
            reply="비슷한 제목이 여러 편이에요.",
            card=None,
            evaluation=None,
            candidates=[
                ChatChoiceDto(title="스파이더맨: 브랜드 뉴 데이", year="2026", slug="tmdb-2")
            ],
        )
        response = await interactor.chat(MovaChatRequest(message="스파이더맨 어때", history=[]))
        self.assertEqual([c.title for c in response.choices], ["스파이더맨: 브랜드 뉴 데이"])
        self.assertEqual(response.to_schema().choices[0].slug, "tmdb-2")

    async def test_booking_records_intent_signal_for_logged_in_user(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatBookingDto
        from mova.app.use_cases.market_chat_booking_interactor import BookingResult

        interactor, repo, _, booking = self._interactor(destination="booking")
        booking.assist.return_value = BookingResult(
            status="ok",
            reply=f"『호프』 {REGION_ASK_MARKER}?",
            card=None,
            booking=ChatBookingDto(
                status="need_region", region=None, theaters=[], booking_links=[]
            ),
            resolved_movie_id=7,
        )

        response = await interactor.chat(
            MovaChatRequest(message="호프 예매하고 싶어", history=[], user_id=3)
        )

        self.assertEqual(response.response_type, "booking")
        repo.record_user_action.assert_awaited_once_with(3, 7, "booking_intent")

    async def test_booking_intent_not_recorded_for_anonymous(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatBookingDto
        from mova.app.use_cases.market_chat_booking_interactor import BookingResult

        interactor, repo, _, booking = self._interactor(destination="booking")
        booking.assist.return_value = BookingResult(
            status="ok",
            reply="r",
            card=None,
            booking=ChatBookingDto(
                status="need_region", region=None, theaters=[], booking_links=[]
            ),
            resolved_movie_id=7,
        )

        await interactor.chat(MovaChatRequest(message="호프 예매하고 싶어", history=[]))

        repo.record_user_action.assert_not_awaited()

    async def test_region_continuation_skips_classifier(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatBookingDto
        from mova.app.use_cases.market_chat_booking_interactor import BookingResult

        interactor, _repo, _, booking = self._interactor(destination="general")
        booking.assist.return_value = BookingResult(
            status="ok",
            reply="영화관 목록",
            card=None,
            booking=ChatBookingDto(status="showing", region="강남", theaters=[], booking_links=[]),
        )
        history = [
            {
                "role": "assistant",
                "content": f"『호프』 상영관을 찾아드릴게요. {REGION_ASK_MARKER}?",
            },
        ]

        response = await interactor.chat(MovaChatRequest(message="강남", history=history))

        self.assertEqual(response.response_type, "booking")
        interactor._classifier.classify.assert_not_awaited()
        self.assertEqual(booking.assist.await_args.kwargs["pending_title"], "호프")

    async def test_booking_lexicon_skips_general_classifier(self) -> None:
        """분류기가 general이라 해도 '시간표' 발화는 booking으로 간다(2026-09-27 실사용)."""
        from mova.app.use_cases.market_chat_booking_interactor import BookingResult

        interactor, _repo, _, booking = self._interactor(destination="general")
        booking.assist.return_value = BookingResult(
            status="ok", reply="『인턴』 상영관을 찾아드릴게요.", card=None, booking=None
        )
        response = await interactor.chat(MovaChatRequest(message="인턴 영화 시간표 보여줘"))
        self.assertEqual(response.response_type, "booking")
        interactor._classifier.classify.assert_not_awaited()
        interactor._general.ask.assert_not_awaited()

    async def test_general_gets_showing_titles_as_grounding(self) -> None:
        interactor, _repo, _, booking = self._interactor(destination="general")
        booking.showing_titles.return_value = ["인턴(2026)", "오디세이(2026)"]
        interactor._general.ask.return_value = MycroftAnswerDto(text="답")
        await interactor.chat(MovaChatRequest(message="인턴 언제 해?"))
        question = interactor._general.ask.await_args.args[0].question
        self.assertIn("[지금 상영 중", question)
        self.assertIn("인턴(2026)", question)

    async def test_pending_region_yields_to_topic_change(self) -> None:
        """지역 되묻기 뒤 "옵세션 줄거리 알려줘"는 지역명이 아니다(2026-09-22 실사용:
        "'옵세션 줄거리 알려줘' 지역을 찾지 못했어요"). 제목이 있고 지명 신호가 없으면
        새 요청으로 본다 — 줄거리 요청이라 결정론으로 evaluate에 간다(09-28, 분류기 생략)."""
        from mova.app.dtos.market_chat_dto import ChatRecommendationDto
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        interactor, repo, evaluation, booking = self._interactor(destination="evaluate")
        repo.find_movie_titled_in_text.return_value = _item(7, "옵세션", "2026")
        evaluation.evaluate.return_value = EvaluationResult(
            status="ok",
            reply="줄거리",
            card=ChatRecommendationDto(
                id="tmdb-7",
                movie_id=7,
                title="옵세션",
                year="2026",
                poster="",
                synopsis="",
                platform=None,
                hook="",
            ),
            evaluation=None,
        )
        history = [
            {"role": "user", "content": "옵세션 예매하고싶어"},
            {
                "role": "assistant",
                "content": f"『옵세션』 상영관을 찾아드릴게요. {REGION_ASK_MARKER}?",
            },
        ]

        response = await interactor.chat(
            MovaChatRequest(message="옵세션 줄거리 알려줘", history=history)
        )

        self.assertEqual(response.response_type, "evaluation")
        self.assertEqual(evaluation.evaluate.await_args.kwargs["entities"], ["옵세션"])
        booking.assist.assert_not_awaited()

    async def test_pending_region_still_taken_for_bare_region(self) -> None:
        """제목 없는 "강남"은 종전대로 지역 답으로 잇는다(화제 전환 방어의 오탐 없음)."""
        from mova.app.dtos.market_chat_dto import ChatBookingDto
        from mova.app.use_cases.market_chat_booking_interactor import BookingResult

        interactor, _repo, _, booking = self._interactor(destination="general")
        booking.assist.return_value = BookingResult(
            status="ok",
            reply="목록",
            card=None,
            booking=ChatBookingDto(status="showing", region="강남", theaters=[], booking_links=[]),
        )
        history = [
            {
                "role": "assistant",
                "content": f"『호프』 상영관을 찾아드릴게요. {REGION_ASK_MARKER}?",
            }
        ]

        await interactor.chat(MovaChatRequest(message="강남", history=history))

        self.assertEqual(booking.assist.await_args.kwargs["pending_title"], "호프")
        interactor._classifier.classify.assert_not_awaited()

    async def test_choice_followup_by_year_routes_to_evaluate(self) -> None:
        """후보 제시 뒤 "26년꺼"는 2026년 후보 선택이다(2026-09-22 실사용: recommend로
        흘러 "26년차 작품"으로 오해). 분류기 없이 evaluate로 잇는다."""
        from mova.app.dtos.market_chat_dto import ChatRecommendationDto
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        interactor, _repo, evaluation, _ = self._interactor(destination="recommend")
        evaluation.evaluate.return_value = EvaluationResult(
            status="ok",
            reply="평가",
            card=ChatRecommendationDto(
                id="tmdb-7",
                movie_id=7,
                title="스파이더맨: 브랜드 뉴 데이",
                year="2026",
                poster="",
                synopsis="",
                platform=None,
                hook="",
            ),
            evaluation=None,
        )
        history = [
            {"role": "user", "content": "스파이더맨 어때"},
            {
                "role": "assistant",
                "content": "비슷한 제목이 여러 편이에요: 스파이더맨: 노 웨이 홈(2021) / "
                "스파이더맨: 어크로스 더 유니버스(2023) / 스파이더맨: 브랜드 뉴 데이(2026). "
                "어떤 작품을 말씀하시나요?",
            },
        ]

        response = await interactor.chat(MovaChatRequest(message="26년꺼", history=history))

        self.assertEqual(response.response_type, "evaluation")
        interactor._classifier.classify.assert_not_awaited()
        self.assertEqual(
            evaluation.evaluate.await_args.kwargs["entities"], ["스파이더맨: 브랜드 뉴 데이"]
        )

    async def test_eval_positive_reaction_records_signal(self) -> None:
        interactor, repo, _, _ = self._interactor(destination="general")
        conversations = AsyncMock()
        conversations.get_owner_id.return_value = 3
        conversations.get_last_evaluation_movie_id.return_value = 7
        conversations.create.return_value = 1
        interactor._conversations = conversations
        interactor._general.ask.return_value = MycroftAnswerDto(text="응답")

        await interactor.chat(
            MovaChatRequest(message="재밌겠다 볼래!", history=[], user_id=3, conversation_id=9)
        )

        repo.record_user_action.assert_awaited_once_with(3, 7, "eval_positive")


class ChatInteractorMarkWatchedTests(unittest.IsolatedAsyncioTestCase):
    """에이전트 mark_watched 터미널 → 봤어요·별점 기록(2026-09-29 v10 선구현)."""

    def _interactor(self) -> tuple[ChatInteractor, AsyncMock]:
        repo = AsyncMock()
        repo.save_chat.return_value = 11
        interactor = ChatInteractor(
            repository=repo,
            recommender=AsyncMock(),
            preferences=AsyncMock(),
            hub_rag=AsyncMock(),
            classifier=AsyncMock(),
            general=AsyncMock(),
            evaluation=AsyncMock(),
            booking=AsyncMock(),
        )
        return interactor, repo

    @staticmethod
    def _decision(arguments: dict[str, str]) -> AgentDecision:
        return AgentDecision(terminal={"name": "mark_watched", "arguments": arguments})

    async def test_records_watched_and_rating(self) -> None:
        interactor, repo = self._interactor()
        repo.search_movies_by_title.return_value = [_item(7, "인셉션", "2010")]
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="인셉션 봤어 4점", history=[], user_id=3),
            "t",
            self._decision({"title": "인셉션", "rating": "4"}),
        )
        repo.record_user_action.assert_awaited_once_with(3, 7, "watched")
        repo.record_rating.assert_awaited_once_with(3, 7, 4.0)
        self.assertIn("봤어요로 표시", resp.reply)
        self.assertIn("4점", resp.reply)

    async def test_records_watched_only_without_rating(self) -> None:
        interactor, repo = self._interactor()
        repo.search_movies_by_title.return_value = [_item(7, "인셉션", "2010")]
        await interactor._act_on_agent(
            MovaChatRequest(message="인셉션 봤어", history=[], user_id=3),
            "t",
            self._decision({"title": "인셉션"}),
        )
        repo.record_user_action.assert_awaited_once_with(3, 7, "watched")
        repo.record_rating.assert_not_awaited()

    async def test_anonymous_user_is_not_recorded(self) -> None:
        interactor, repo = self._interactor()
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="인셉션 봤어 4점", history=[], user_id=None),
            "t",
            self._decision({"title": "인셉션", "rating": "4"}),
        )
        repo.record_user_action.assert_not_awaited()
        repo.record_rating.assert_not_awaited()
        self.assertIn("로그인", resp.reply)

    async def test_unresolved_title_asks_again_and_does_not_record(self) -> None:
        interactor, repo = self._interactor()
        repo.search_movies_by_title.return_value = []  # 카탈로그 미일치
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="없는영화 봤어 4점", history=[], user_id=3),
            "t",
            self._decision({"title": "없는영화", "rating": "4"}),
        )
        repo.record_user_action.assert_not_awaited()
        repo.record_rating.assert_not_awaited()
        self.assertIn("못 찾았", resp.reply)

    # --- 2026-09-30 실사용 회귀: 풀네임·연도 꼬리·후보 선택 이어받기 ---

    _SPIDEY = (
        (1, "스파이더맨: 노 웨이 홈", "2021"),
        (2, "스파이더맨: 어크로스 더 유니버스", "2023"),
        (3, "스파이더맨: 브랜드 뉴 데이", "2026"),
    )

    async def test_year_suffixed_title_is_resolved(self) -> None:
        interactor, repo = self._interactor()
        repo.search_movies_by_title.return_value = [_item(3, "스파이더맨: 브랜드 뉴 데이", "2026")]
        await interactor._act_on_agent(
            MovaChatRequest(message="그거 봤다고", history=[], user_id=3),
            "t",
            self._decision({"title": "스파이더맨: 브랜드 뉴 데이(2026)"}),
        )
        repo.record_user_action.assert_awaited_once_with(3, 3, "watched")

    async def test_partial_title_with_single_match_is_resolved(self) -> None:
        interactor, repo = self._interactor()
        repo.search_movies_by_title.return_value = [_item(3, "스파이더맨: 브랜드 뉴 데이", "2026")]
        await interactor._act_on_agent(
            MovaChatRequest(message="브랜드 뉴 데이 봤어", history=[], user_id=3),
            "t",
            self._decision({"title": "브랜드 뉴 데이"}),
        )
        repo.record_user_action.assert_awaited_once_with(3, 3, "watched")

    async def test_ambiguous_title_asks_with_choice_list(self) -> None:
        interactor, repo = self._interactor()
        repo.search_movies_by_title.return_value = [_item(*m) for m in self._SPIDEY]
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="스파이더맨 봤어", history=[], user_id=3),
            "t",
            self._decision({"title": "스파이더맨"}),
        )
        repo.record_user_action.assert_not_awaited()
        self.assertIn("어떤 작품을 보셨나요?", resp.reply)
        # 되묻기 문구는 다음 턴에 그대로 되읽힌다
        self.assertEqual(
            pick_from_choice_list(resp.reply, "2026작품이겠지? 최신이면"),
            ("스파이더맨: 브랜드 뉴 데이", "watched"),
        )

    async def test_rating_glued_to_title_is_split(self) -> None:
        interactor, repo = self._interactor()
        hit = [_item(2, "스파이더맨: 어크로스 더 유니버스", "2023")]
        repo.search_movies_by_title.side_effect = lambda terms, _n: (
            hit if terms == ["어크로스 더 유니버스"] else []
        )
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="어크로스 더 유니버스 봤어 4점", history=[], user_id=3),
            "t",
            self._decision({"title": "어크로스 더 유니버스 4"}),
        )
        repo.record_user_action.assert_awaited_once_with(3, 2, "watched")
        repo.record_rating.assert_awaited_once_with(3, 2, 4.0)
        self.assertIn("4점", resp.reply)

    async def test_ambiguous_title_narrowed_by_previous_reply(self) -> None:
        interactor, repo = self._interactor()
        repo.search_movies_by_title.return_value = [_item(*m) for m in self._SPIDEY]
        history = [
            {"role": "user", "content": "요즘 뭐해"},
            {"role": "assistant", "content": "『스파이더맨: 브랜드 뉴 데이』가 상영 중이에요."},
        ]
        await interactor._act_on_agent(
            MovaChatRequest(message="스파이더맨 봤어", history=history, user_id=3),
            "t",
            self._decision({"title": "스파이더맨"}),
        )
        repo.record_user_action.assert_awaited_once_with(3, 3, "watched")


class ChatInteractorAgentTasteTests(unittest.IsolatedAsyncioTestCase):
    """에이전트 recommend_for_me·similar_to·taste_profile 터미널 분기(2026-09-29 v10 선구현)."""

    def _interactor(self) -> tuple[ChatInteractor, AsyncMock]:
        repo = AsyncMock()
        repo.save_chat.return_value = 11
        interactor = ChatInteractor(
            repository=repo,
            recommender=AsyncMock(),
            preferences=AsyncMock(),
            hub_rag=AsyncMock(),
            classifier=AsyncMock(),
            general=AsyncMock(),
            evaluation=AsyncMock(),
            booking=AsyncMock(),
            movies=AsyncMock(),
            taste_vectors=AsyncMock(),
        )
        return interactor, repo

    async def test_recommend_for_me_dispatches_taste_mode(self) -> None:
        interactor, _ = self._interactor()
        interactor._reply_personal_recommend = AsyncMock(return_value="R")  # type: ignore[method-assign]
        await interactor._act_on_agent(
            MovaChatRequest(message="내 취향 추천", history=[], user_id=3),
            "t",
            AgentDecision(terminal={"name": "recommend_for_me", "arguments": {"query": "내 취향"}}),
        )
        interactor._reply_personal_recommend.assert_awaited_once()
        self.assertIsNone(interactor._reply_personal_recommend.await_args.kwargs["seed_title"])

    async def test_similar_to_dispatches_with_seed_title(self) -> None:
        interactor, _ = self._interactor()
        interactor._reply_personal_recommend = AsyncMock(return_value="R")  # type: ignore[method-assign]
        await interactor._act_on_agent(
            MovaChatRequest(message="기생충 같은 영화", history=[], user_id=3),
            "t",
            AgentDecision(terminal={"name": "similar_to", "arguments": {"title": "기생충"}}),
        )
        self.assertEqual(
            interactor._reply_personal_recommend.await_args.kwargs["seed_title"], "기생충"
        )

    async def test_taste_profile_summarizes_genres_and_top_titles(self) -> None:
        interactor, repo = self._interactor()
        interactor._taste_vectors.list_user_ratings.return_value = [(7, 4.5), (8, 3.0)]
        repo.get_watched_movie_ids.return_value = {"7", "9"}
        interactor._preferences.get_preferences.return_value = UserPreferenceDto(
            nickname="냥", preferred_genres=["SF"]
        )
        repo.get_catalog_items.return_value = [
            MovaSearchItemSchema(
                id="7",
                title="인셉션",
                year="2010",
                rating=4.0,
                poster="",
                match_type="s",
                genres="SF, 스릴러",
            ),
            MovaSearchItemSchema(
                id="8",
                title="컨택트",
                year="2016",
                rating=4.0,
                poster="",
                match_type="s",
                genres="SF, 드라마",
            ),
            MovaSearchItemSchema(
                id="9",
                title="인터스텔라",
                year="2014",
                rating=4.0,
                poster="",
                match_type="s",
                genres="SF",
            ),
        ]
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="내 취향이 뭐야", history=[], user_id=3),
            "t",
            AgentDecision(terminal={"name": "taste_profile", "arguments": {}}),
        )
        self.assertIn("SF", resp.reply)  # 최다 장르
        self.assertIn("인셉션", resp.reply)  # 최고 별점 작품
        self.assertIn("별점 2편", resp.reply)

    async def test_taste_profile_without_history_guides_user(self) -> None:
        interactor, repo = self._interactor()
        interactor._taste_vectors.list_user_ratings.return_value = []
        repo.get_watched_movie_ids.return_value = set()
        interactor._preferences.get_preferences.return_value = UserPreferenceDto.empty()
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="내 취향이 뭐야", history=[], user_id=3),
            "t",
            AgentDecision(terminal={"name": "taste_profile", "arguments": {}}),
        )
        self.assertIn("아직 취향을 파악할 기록이 없어요", resp.reply)
        repo.get_catalog_items.assert_not_awaited()

    async def test_taste_profile_anonymous_asks_login(self) -> None:
        interactor, _ = self._interactor()
        resp = await interactor._act_on_agent(
            MovaChatRequest(message="내 취향이 뭐야", history=[], user_id=None),
            "t",
            AgentDecision(terminal={"name": "taste_profile", "arguments": {}}),
        )
        self.assertIn("로그인", resp.reply)
        interactor._taste_vectors.list_user_ratings.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()


class FallbackHonestyPromptTests(unittest.TestCase):
    def test_popular_fallback_catalog_gets_honesty_instruction(self) -> None:
        from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder

        hits = [
            MovaSearchItemSchema(
                id="1", title="A", year="2020", rating=4.0, poster="", match_type="popular_fallback"
            ),
            MovaSearchItemSchema(
                id="2", title="B", year="2021", rating=4.5, poster="", match_type="popular_fallback"
            ),
        ]
        section = ChatPromptBuilder().format_tag_catalog_section(hits)
        self.assertIn("폴백 후보", section)
        self.assertIn("정직하게", section)

    def test_matched_catalog_has_no_honesty_instruction(self) -> None:
        from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder

        hits = [
            MovaSearchItemSchema(
                id="1", title="A", year="2020", rating=4.0, poster="", match_type="keyword"
            ),
            MovaSearchItemSchema(
                id="2", title="B", year="2021", rating=4.5, poster="", match_type="popular_fallback"
            ),
        ]
        section = ChatPromptBuilder().format_tag_catalog_section(hits)
        self.assertNotIn("폴백 후보", section)


class ChoiceListPickerTests(unittest.TestCase):
    _EVAL = (
        "비슷한 제목이 여러 편이에요: 스파이더맨: 노 웨이 홈(2021) / "
        "스파이더맨: 어크로스 더 유니버스(2023) / 스파이더맨: 브랜드 뉴 데이(2026). "
        "어떤 작품을 말씀하시나요?"
    )
    _BOOK = "비슷한 제목이 여러 편이에요: 군체(2026) / 구원자(2025) / 감자(1987). 어떤 작품을 예매하시려나요?"

    def test_year_two_digit(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._EVAL, "26년꺼"), ("스파이더맨: 브랜드 뉴 데이", "evaluate")
        )

    def test_year_four_digit(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._EVAL, "2021년 거"), ("스파이더맨: 노 웨이 홈", "evaluate")
        )

    def test_ordinal(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._EVAL, "두번째"),
            ("스파이더맨: 어크로스 더 유니버스", "evaluate"),
        )

    # 에이전트 search_movie가 만드는 되묻기(꼬리 "어떤 작품인가요?")
    _AGENT = (
        "비슷한 제목이 여러 편이에요: 스파이더맨: 노 웨이 홈(2021) / "
        "스파이더맨: 어크로스 더 유니버스(2023) / 스파이더맨: 브랜드 뉴 데이(2026). 어떤 작품인가요?"
    )

    def test_watched_track_from_previous_user_message(self) -> None:
        self.assertEqual(
            pick_from_choice_list(
                self._AGENT, "2026작품이겠지? 최신이면", "스파이더맨 최신꺼 봤어"
            ),
            ("스파이더맨: 브랜드 뉴 데이", "watched"),
        )

    def test_watched_track_from_current_message_with_typo(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._AGENT, "브랜드ㅡ 뉴 데이 봤어;;;;;;;;"),
            ("스파이더맨: 브랜드 뉴 데이", "watched"),
        )

    def test_agent_list_without_watched_cue_goes_back_to_agent(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._AGENT, "2026년꺼", "스파이더맨 누가 나와"),
            ("스파이더맨: 브랜드 뉴 데이", "agent"),
        )

    def test_newest_picks_latest_year(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._EVAL, "최신꺼"), ("스파이더맨: 브랜드 뉴 데이", "evaluate")
        )

    def test_question_about_watching_is_not_watched_track(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._EVAL, "두번째", "예고편 봤는데 어때?"),
            ("스파이더맨: 어크로스 더 유니버스", "evaluate"),
        )

    def test_title_fragment(self) -> None:
        self.assertEqual(
            pick_from_choice_list(self._EVAL, "브랜드 뉴 데이요"),
            ("스파이더맨: 브랜드 뉴 데이", "evaluate"),
        )

    def test_booking_track_from_tail(self) -> None:
        self.assertEqual(pick_from_choice_list(self._BOOK, "1987"), ("감자", "booking"))

    def test_ambiguous_or_unrelated_is_none(self) -> None:
        self.assertIsNone(pick_from_choice_list(self._EVAL, "스파이더맨"))  # 셋 다 부분일치
        self.assertIsNone(pick_from_choice_list(self._EVAL, "다른 영화 추천해줘"))
        self.assertIsNone(pick_from_choice_list("안녕하세요!", "26년꺼"))


class ShowtimeDateParsingTests(unittest.TestCase):
    """예매 발화의 날짜 표현 → YYYY-MM-DD(KST). 2026-09-28 "9월 30일자로 찾아줘" 실사용."""

    def test_words_and_month_day(self) -> None:
        from datetime import datetime

        from mova.app.use_cases.market_chat_booking_interactor import parse_showtime_date

        today = datetime(2026, 9, 28)
        self.assertEqual(parse_showtime_date("오늘 몇 시에 해?", today=today), "2026-09-28")
        self.assertEqual(parse_showtime_date("내일 볼 수 있어?", today=today), "2026-09-29")
        self.assertEqual(parse_showtime_date("모레는?", today=today), "2026-09-30")
        self.assertEqual(parse_showtime_date("9월 30일자로 찾아줘", today=today), "2026-09-30")
        self.assertEqual(parse_showtime_date("10월 2일에", today=today), "2026-10-02")
        self.assertEqual(parse_showtime_date("30일자로", today=today), "2026-09-30")
        self.assertEqual(
            parse_showtime_date("3일에 볼래", today=today), "2026-10-03"
        )  # 지난 날 → 다음 달

    def test_no_date(self) -> None:
        from datetime import datetime

        from mova.app.use_cases.market_chat_booking_interactor import parse_showtime_date

        today = datetime(2026, 9, 28)
        for msg in ("인턴 예매하고 싶어", "군자", "2관에서", "1일 1영화"):
            self.assertIsNone(parse_showtime_date(msg, today=today), msg)


class WideAreaDetectionTests(unittest.TestCase):
    def test_wide_areas(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import wide_area

        for msg, want in (
            ("서울", "서울"),
            ("서울 전체", "서울"),
            ("서울특별시", "서울"),
            ("경기도", "경기"),
            ("부산 전역", "부산"),
        ):
            self.assertEqual(wide_area(msg), want, msg)

    def test_points_are_not_wide(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import wide_area

        for msg in ("강남", "서울역", "서울대입구", "홍대입구역", "군자", None):
            self.assertIsNone(wide_area(msg), msg)


class DistrictDetectionTests(unittest.TestCase):
    def test_districts(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import district_of

        for msg, want in (
            ("강남구", "강남구"),
            ("서울 강남구", "강남구"),
            ("마포구 전체", "마포구"),
            ("양평군", "양평군"),
        ):
            self.assertEqual(district_of(msg), want, msg)
        for msg in ("강남", "강남역", "서울", "강남구청역", "구로디지털단지", None):
            self.assertIsNone(district_of(msg), msg)


class RegionTransportParsingTests(unittest.TestCase):
    def test_car_widens_radius(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import _parse_region_transport

        region, radius, label = _parse_region_transport("강남 차로 갈게")
        self.assertEqual((region, radius, label), ("강남", 20_000, "차량"))

    def test_walk_narrows_radius(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import _parse_region_transport

        region, radius, label = _parse_region_transport("홍대입구역 도보")
        self.assertEqual((region, radius, label), ("홍대입구역", 3_000, "도보"))

    def test_near_tail_stripped(self) -> None:
        """'군자역 근처'를 그대로 넘기면 카카오 지오코딩이 실패한다(2026-09-22 실측)."""
        from mova.app.use_cases.market_chat_booking_interactor import _parse_region_transport

        region, radius, label = _parse_region_transport("군자역 근처")
        self.assertEqual((region, radius, label), ("군자역", 10_000, None))

    def test_near_tail_stripped_with_transport(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import _parse_region_transport

        region, radius, label = _parse_region_transport("강남 주변 차로")
        self.assertEqual((region, radius, label), ("강남", 20_000, "차량"))

    def test_plain_region_keeps_default(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import _parse_region_transport

        region, radius, label = _parse_region_transport("수원")
        self.assertEqual((region, radius, label), ("수원", 10_000, None))


class BookingShowtimeTests(unittest.IsolatedAsyncioTestCase):
    """Phase 2 — 롯데시네마 시간표 연동."""

    def _service_with_showtimes(
        self, *, showtimes_result: object | None = "default"
    ) -> BookingAssistService:
        from mova.app.dtos.market_chat_dto import CinemaShowtimeDto, ShowtimeSlotDto

        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(7, "호프")]
        movies = AsyncMock()
        movies.find_by_id.return_value = _detail(7, "호프")
        box_office = AsyncMock()
        entry = AsyncMock()
        entry.title = "호프"
        box_office.fetch_box_office.return_value = [entry]
        theaters = AsyncMock()
        showtime_port = AsyncMock()
        if showtimes_result == "default":
            showtime_port.fetch_showtimes.return_value = CinemaShowtimeDto(
                cinema_name="롯데시네마 강남",
                slots=[
                    ShowtimeSlotDto(
                        screen="1관",
                        start_time="14:00",
                        end_time="16:00",
                        film_type="2D",
                        seats_available=50,
                        seats_total=120,
                    )
                ],
            )
        else:
            showtime_port.fetch_showtimes.return_value = showtimes_result
        return BookingAssistService(
            repository=repo,
            movies=movies,
            box_office=box_office,
            theaters=theaters,
            showtimes=showtime_port,
        )

    async def test_date_followup_keeps_movie_and_region(self) -> None:
        """ "9월 30일자로 찾아줘" — 직전 예매 응답(『옵세션』 '서울' 근처 …)의 작품·지역을 잇고
        시간표를 그 날짜로 조회한다(2026-09-28 실사용: 제목을 되묻던 문제)."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes()
        service._showtimes.find_showing_cinemas.return_value = []
        service._repository.find_movie_titled_in_text.return_value = _item(7, "호프")
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 강남", address="서울", distance_m=200, place_url="", phone=""
            )
        ]
        history = [
            {"role": "user", "content": "서울 전체로 찾아줘"},
            {
                "role": "assistant",
                "content": "『호프』 — '서울' 근처(반경 10km) 영화관 5곳을 가까운 순으로 찾았어요.",
            },
        ]
        result = await service.assist_slots(
            message="9월 30일자로 찾아줘",
            title_text=None,
            verified_title=None,
            region=None,
            trace_id="t",
            history=history,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.booking.region, "서울")
        # '서울'은 광역이라 서울 롯데관 전체 조회로 간다 — 날짜가 그대로 넘어가야 한다.
        self.assertTrue(
            service._showtimes.find_showing_cinemas.await_args.kwargs["date"].endswith("-09-30")
        )
        self.assertIn("『호프』", result.reply)
        # 날짜 라벨은 오늘 기준으로 "내일"·"오늘"로 바뀐다(09-29 실측: 9/29에 돌리면 '내일') — 문자열 고정 금지
        self.assertTrue(
            any(x in result.reply for x in ("9월 30일", "내일", "오늘", "9/30")),
            result.reply,
        )

    async def test_showing_reply_carries_title_marker(self) -> None:
        """예매 결과 문구에 『제목』이 들어가야 다음 턴이 작품을 되찾는다."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes()
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(name="CGV 강남", address="서울", distance_m=300, place_url="", phone="")
        ]
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )
        self.assertIn("『호프』", result.reply)
        self.assertIn("'강남' 근처", result.reply)

    async def test_wide_area_scans_area_cinemas_without_kakao(self) -> None:
        """ "서울 전체" — 카카오 반경 검색 대신 서울 롯데관 전부에서 상영관만 모은다(2026-09-28)."""
        from mova.app.dtos.market_chat_dto import CinemaShowtimeDto, ShowtimeSlotDto

        service = self._service_with_showtimes()
        slot = ShowtimeSlotDto(
            screen="3관",
            start_time="23:50",
            end_time="01:40",
            film_type="2D",
            seats_available=10,
            seats_total=100,
        )
        service._showtimes.find_showing_cinemas.return_value = [
            CinemaShowtimeDto(cinema_name=f"롯데시네마 {n}", slots=[slot]) for n in "ABCDEFG"
        ]
        from datetime import datetime
        from unittest.mock import patch

        with patch(
            "mova.app.use_cases.market_chat_booking_interactor._kst_today",
            return_value=datetime(2026, 9, 28, 10, 0),
        ):
            result = await service.assist(
                message="서울 전체", entities=[], trace_id="t", pending_title="호프"
            )

        service._theaters.search_theaters.assert_not_awaited()
        self.assertEqual(service._showtimes.find_showing_cinemas.await_args.args[0], "서울")
        self.assertIn("'서울' 전역", result.reply)
        self.assertIn("7곳", result.reply)
        self.assertEqual(len(result.booking.showtimes), 5)
        self.assertEqual(result.booking.region, "서울")

    async def test_district_scans_radius_around_district_center(self) -> None:
        """ "강남구" — 구 중심(카카오 좌표) 반경 5km 롯데관에서 상영관만, 카카오 극장 검색은 안 탄다."""
        from datetime import datetime
        from unittest.mock import patch

        from mova.app.dtos.market_chat_dto import CinemaShowtimeDto, ShowtimeSlotDto

        service = self._service_with_showtimes()
        service._theaters.resolve_point.return_value = (37.5172, 127.0473)
        slot = ShowtimeSlotDto(
            screen="1관",
            start_time="20:00",
            end_time="",
            film_type="",
            seats_available=5,
            seats_total=90,
        )
        service._showtimes.find_showing_cinemas_near.return_value = [
            CinemaShowtimeDto(cinema_name="롯데시네마 도곡", slots=[slot])
        ]
        with patch(
            "mova.app.use_cases.market_chat_booking_interactor._kst_today",
            return_value=datetime(2026, 9, 28, 10, 0),
        ):
            result = await service.assist(
                message="강남구", entities=[], trace_id="t", pending_title="호프"
            )

        service._theaters.search_theaters.assert_not_awaited()
        args = service._showtimes.find_showing_cinemas_near.await_args
        self.assertEqual(args.args[:2], (37.5172, 127.0473))
        self.assertIn("'강남구' 일대", result.reply)
        self.assertIn("롯데시네마 도곡 20:00", result.reply)

    def test_wide_drops_past_slots_and_sorts_by_next(self) -> None:
        from datetime import datetime
        from unittest.mock import patch

        from mova.app.dtos.market_chat_dto import CinemaShowtimeDto, ShowtimeSlotDto
        from mova.app.use_cases.market_chat_booking_interactor import _drop_past_slots

        def slot(t: str) -> ShowtimeSlotDto:
            return ShowtimeSlotDto(
                screen="1관",
                start_time=t,
                end_time="",
                film_type="",
                seats_available=1,
                seats_total=1,
            )

        showing = [
            CinemaShowtimeDto(cinema_name="김포공항", slots=[slot("12:30"), slot("22:20")]),
            CinemaShowtimeDto(cinema_name="월드타워", slots=[slot("13:10")]),
            CinemaShowtimeDto(cinema_name="지난것만", slots=[slot("09:00")]),
        ]
        with patch(
            "mova.app.use_cases.market_chat_booking_interactor._kst_today",
            return_value=datetime(2026, 9, 28, 12, 40),
        ):
            kept = _drop_past_slots(showing, None)
            other_day = _drop_past_slots(showing, "2026-09-29")
        self.assertEqual([c.cinema_name for c in kept], ["월드타워", "김포공항"])
        self.assertEqual([s.start_time for s in kept[1].slots], ["22:20"])
        self.assertEqual(len(other_day), 3)  # 다른 날은 그대로

    async def test_lotte_theater_gets_showtimes(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes()
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 강남", address="서울", distance_m=200, place_url="", phone=""
            )
        ]
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(len(result.booking.showtimes), 1)
        self.assertEqual(result.booking.showtimes[0].cinema_name, "롯데시네마 강남")
        self.assertEqual(result.booking.showtimes[0].slots[0].screen, "1관")
        self.assertIn("롯데시네마 기준", result.reply)

    async def test_non_lotte_theater_skips_showtime_fetch(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes()
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(name="CGV 강남", address="서울", distance_m=300, place_url="", phone="")
        ]
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(result.booking.showtimes, [])
        service._showtimes.fetch_showtimes.assert_not_awaited()

    async def test_no_showtime_port_returns_empty(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(7, "호프")]
        movies = AsyncMock()
        movies.find_by_id.return_value = _detail(7, "호프")
        box_office = AsyncMock()
        entry = AsyncMock()
        entry.title = "호프"
        box_office.fetch_box_office.return_value = [entry]
        theaters = AsyncMock()
        theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 강남", address="서울", distance_m=200, place_url="", phone=""
            )
        ]
        service = BookingAssistService(
            repository=repo, movies=movies, box_office=box_office, theaters=theaters
        )
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(result.booking.showtimes, [])

    async def test_showtime_exception_is_swallowed(self) -> None:
        """시간표 조회 예외 시 크래시 없이 빈 리스트로 폴백한다."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes()
        service._showtimes.fetch_showtimes.side_effect = RuntimeError("network")
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 건대입구", address="서울", distance_m=500, place_url="", phone=""
            )
        ]
        result = await service.assist(
            message="건대", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(result.booking.showtimes, [])
        self.assertEqual(result.status, "ok")

    async def test_max_two_cinemas_cap(self) -> None:
        """롯데시네마가 3곳이어도 시간표는 최대 2곳만 조회한다."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto, CinemaShowtimeDto, ShowtimeSlotDto

        service = self._service_with_showtimes()
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 강남", address="서울", distance_m=100, place_url="", phone=""
            ),
            ChatTheaterDto(
                name="롯데시네마 건대", address="서울", distance_m=200, place_url="", phone=""
            ),
            ChatTheaterDto(
                name="롯데시네마 홍대", address="서울", distance_m=300, place_url="", phone=""
            ),
        ]
        call_count = 0

        async def _side_effect(name: str, title: str, **kw: object) -> CinemaShowtimeDto:
            nonlocal call_count
            call_count += 1
            return CinemaShowtimeDto(
                cinema_name=name,
                slots=[
                    ShowtimeSlotDto(
                        screen="1관",
                        start_time="14:00",
                        end_time="16:00",
                        film_type="2D",
                        seats_available=50,
                        seats_total=100,
                    )
                ],
            )

        service._showtimes.fetch_showtimes.side_effect = _side_effect
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(len(result.booking.showtimes), 2)
        self.assertEqual(call_count, 2)

    async def test_showtime_none_result_excluded(self) -> None:
        """fetch_showtimes가 None을 반환하면 결과에 포함되지 않는다."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes(showtimes_result=None)
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 강남", address="서울", distance_m=200, place_url="", phone=""
            )
        ]
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(result.booking.showtimes, [])

    async def test_showtime_reply_includes_slot_count(self) -> None:
        """시간표가 있으면 응답에 회차 수가 포함된다."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto, CinemaShowtimeDto, ShowtimeSlotDto

        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(7, "호프")]
        movies = AsyncMock()
        movies.find_by_id.return_value = _detail(7, "호프")
        box_office = AsyncMock()
        entry = AsyncMock()
        entry.title = "호프"
        box_office.fetch_box_office.return_value = [entry]
        theaters = AsyncMock()
        theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 강남", address="서울", distance_m=200, place_url="", phone=""
            ),
        ]
        showtime_port = AsyncMock()
        showtime_port.fetch_showtimes.return_value = CinemaShowtimeDto(
            cinema_name="롯데시네마 강남",
            slots=[
                ShowtimeSlotDto(
                    screen="1관",
                    start_time="14:00",
                    end_time="16:00",
                    film_type="2D",
                    seats_available=50,
                    seats_total=120,
                ),
                ShowtimeSlotDto(
                    screen="2관",
                    start_time="17:00",
                    end_time="19:00",
                    film_type="IMAX",
                    seats_available=30,
                    seats_total=80,
                ),
            ],
        )
        service = BookingAssistService(
            repository=repo,
            movies=movies,
            box_office=box_office,
            theaters=theaters,
            showtimes=showtime_port,
        )
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertIn("2회차", result.reply)

    async def test_nearest_fallback_when_no_lotte_in_kakao(self) -> None:
        """카카오 결과에 롯데가 없으면 좌표 기반 최근접 롯데시네마를 찾는다."""
        from mova.app.dtos.market_chat_dto import (
            ChatTheaterDto,
            CinemaShowtimeDto,
            ShowtimeSlotDto,
        )

        service = self._service_with_showtimes()
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="CGV 강남",
                address="서울",
                distance_m=300,
                place_url="",
                phone="",
                lat=37.498,
                lng=127.028,
            )
        ]
        service._showtimes.fetch_nearest_showtimes.return_value = CinemaShowtimeDto(
            cinema_name="롯데시네마 도곡",
            slots=[
                ShowtimeSlotDto(
                    screen="1관",
                    start_time="15:00",
                    end_time="17:00",
                    film_type="2D",
                    seats_available=40,
                    seats_total=100,
                )
            ],
        )
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        service._showtimes.fetch_nearest_showtimes.assert_awaited_once()
        self.assertEqual(len(result.booking.showtimes), 1)
        self.assertEqual(result.booking.showtimes[0].cinema_name, "롯데시네마 도곡")

    async def test_nearest_fallback_not_called_when_lotte_found(self) -> None:
        """카카오 결과에 롯데가 있으면 최근접 폴백은 호출하지 않는다."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes()
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(
                name="롯데시네마 강남",
                address="서울",
                distance_m=200,
                place_url="",
                phone="",
                lat=37.498,
                lng=127.028,
            )
        ]
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(len(result.booking.showtimes), 1)
        service._showtimes.fetch_nearest_showtimes.assert_not_awaited()

    async def test_nearest_fallback_skipped_without_coords(self) -> None:
        """좌표 없는 극장만 있으면 최근접 폴백을 시도하지 않는다."""
        from mova.app.dtos.market_chat_dto import ChatTheaterDto

        service = self._service_with_showtimes()
        service._theaters.search_theaters.return_value = [
            ChatTheaterDto(name="CGV 강남", address="서울", distance_m=300, place_url="", phone="")
        ]
        result = await service.assist(
            message="강남", entities=[], trace_id="t", pending_title="호프"
        )

        self.assertEqual(result.booking.showtimes, [])
        service._showtimes.fetch_nearest_showtimes.assert_not_awaited()


class ShowtimeDtoSerializationTests(unittest.TestCase):
    def test_response_dto_to_schema_includes_showtimes(self) -> None:
        """ChatResponseDto.to_schema()가 booking 시간표를 정상 직렬화한다."""
        from mova.app.dtos.market_chat_dto import (
            ChatBookingDto,
            ChatBookingLinkDto,
            ChatResponseDto,
            CinemaShowtimeDto,
            ShowtimeSlotDto,
        )

        dto = ChatResponseDto(
            chat_id=1,
            reply="테스트",
            refined_query="",
            keywords=[],
            intent_type="booking",
            search_filters={},
            recommendations=[],
            response_type="booking",
            booking=ChatBookingDto(
                status="showing",
                region="강남",
                theaters=[],
                booking_links=[ChatBookingLinkDto(chain="CGV", url="http://cgv")],
                showtimes=[
                    CinemaShowtimeDto(
                        cinema_name="롯데시네마 강남",
                        slots=[
                            ShowtimeSlotDto(
                                screen="1관",
                                start_time="14:00",
                                end_time="16:00",
                                film_type="2D",
                                seats_available=50,
                                seats_total=120,
                            )
                        ],
                    )
                ],
            ),
        )
        schema = dto.to_schema()

        self.assertEqual(len(schema.booking.showtimes), 1)
        self.assertEqual(schema.booking.showtimes[0].cinema_name, "롯데시네마 강남")
        self.assertEqual(len(schema.booking.showtimes[0].slots), 1)
        self.assertEqual(schema.booking.showtimes[0].slots[0].screen, "1관")
        self.assertEqual(schema.booking.showtimes[0].slots[0].seats_available, 50)


class BookingTransportRadiusTests(unittest.IsolatedAsyncioTestCase):
    async def test_region_with_car_passes_wider_radius(self) -> None:
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(7, "호프")]
        movies = AsyncMock()
        movies.find_by_id.return_value = _detail(7, "호프")
        theaters = AsyncMock()
        theaters.search_theaters.return_value = []
        service = BookingAssistService(
            repository=repo, movies=movies, box_office=AsyncMock(), theaters=theaters
        )

        result = await service.assist(
            message="강남 차로 갈게", entities=[], trace_id="t", pending_title="호프"
        )

        theaters.search_theaters.assert_awaited_once_with("강남", radius_m=20_000)
        self.assertEqual(result.booking.region, "강남")
        self.assertIn("차량 기준 반경 20km", result.reply)


class TrackMetaPayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_evaluation_meta_contains_full_payload(self) -> None:
        from mova.app.dtos.market_chat_dto import ChatEvaluationDto, ChatRecommendationDto
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        repo = AsyncMock()
        repo.save_chat.return_value = 11
        classifier = AsyncMock()
        classifier.classify.return_value = ("evaluate", ["호프"])
        evaluation = AsyncMock()
        evaluation.evaluate.return_value = EvaluationResult(
            status="ok",
            reply="평가",
            card=ChatRecommendationDto(
                id="tmdb-7",
                movie_id=7,
                title="호프",
                year="2021",
                poster="",
                synopsis="",
                platform=None,
                hook="",
            ),
            evaluation=ChatEvaluationDto(
                movie_id=7,
                review_count=5,
                avg_rating=4.5,
                tmdb_rating=4.2,
                excerpts=["좋다"],
            ),
        )
        conversations = AsyncMock()
        conversations.get_owner_id.return_value = 3
        conversations.get_last_evaluation_movie_id.return_value = None
        interactor = ChatInteractor(
            repository=repo,
            recommender=AsyncMock(),
            preferences=AsyncMock(),
            hub_rag=AsyncMock(),
            classifier=classifier,
            general=AsyncMock(),
            conversations=conversations,
            evaluation=evaluation,
            booking=AsyncMock(),
        )

        await interactor.chat(
            MovaChatRequest(message="호프 어때??", history=[], user_id=3, conversation_id=9)
        )

        # append_message(assistant) 호출의 meta에 payload 전체가 실렸는지
        assistant_call = conversations.append_message.await_args_list[-1]
        meta = assistant_call.args[3]
        self.assertEqual(meta["evaluation"]["review_count"], 5)
        self.assertEqual(meta["evaluation"]["excerpts"], ["좋다"])
