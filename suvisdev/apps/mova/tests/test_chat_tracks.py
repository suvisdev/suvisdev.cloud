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
from mova.app.dtos.market_chat_dto import ReviewAggregateDto  # noqa: E402
from mova.app.dtos.studio_movies_dto import MovieDetailDto, PlatformDto  # noqa: E402
from mova.app.use_cases.market_chat_booking_interactor import (  # noqa: E402
    REGION_ASK_MARKER,
    BookingAssistService,
    pending_title_from_history,
)
from mova.app.use_cases.market_chat_evaluation_interactor import (  # noqa: E402
    MovieEvaluationService,
)
from mova.app.use_cases.market_chat_interactor import ChatInteractor  # noqa: E402
from mova.app.use_cases.market_chat_title_resolver import (  # noqa: E402
    resolve_movie_title,
)
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
        res = await resolve_movie_title(repo, message="없는영화 어때", entities=[])
        self.assertEqual(res.status, "not_found")


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

    async def test_ok_builds_card_and_payload(self) -> None:
        service, general = self._service()
        result = await service.evaluate(message="호프 어때??", entities=["호프"], trace_id="t")

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.reply, "객관 평가 텍스트")
        self.assertEqual(result.card.movie_id, 7)
        self.assertEqual(result.evaluation.review_count, 5)
        question = general.ask.await_args.args[0].question
        self.assertIn("자체 리뷰 발췌", question)
        self.assertIn("TMDB 리뷰 발췌", question)
        self.assertNotIn("표본 부족", question)

    async def test_small_sample_is_flagged_in_prompt(self) -> None:
        """정직성 규칙 — 리뷰 3건 미만이면 표본 부족을 LLM 입력에 명시한다."""
        service, general = self._service(review_count=1)
        await service.evaluate(message="호프 어때??", entities=["호프"], trace_id="t")
        self.assertIn("표본 부족", general.ask.await_args.args[0].question)

    async def test_not_found_returns_honest_reply(self) -> None:
        service, _ = self._service()
        service._repository.search_movies_by_title.return_value = []
        result = await service.evaluate(message="없는영화 어때", entities=[], trace_id="t")
        self.assertEqual(result.status, "not_found")
        self.assertIsNone(result.card)


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
        self.assertIn("Netflix", result.reply)

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


class ChatInteractorTrackDelegationTests(unittest.IsolatedAsyncioTestCase):
    def _interactor(
        self, *, destination: str
    ) -> tuple[ChatInteractor, AsyncMock, AsyncMock, AsyncMock]:
        repo = AsyncMock()
        repo.save_chat.return_value = 11
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


class RegionTransportParsingTests(unittest.TestCase):
    def test_car_widens_radius(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import _parse_region_transport

        region, radius, label = _parse_region_transport("강남 차로 갈게")
        self.assertEqual((region, radius, label), ("강남", 20_000, "차량"))

    def test_walk_narrows_radius(self) -> None:
        from mova.app.use_cases.market_chat_booking_interactor import _parse_region_transport

        region, radius, label = _parse_region_transport("홍대입구역 도보")
        self.assertEqual((region, radius, label), ("홍대입구역", 3_000, "도보"))

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
