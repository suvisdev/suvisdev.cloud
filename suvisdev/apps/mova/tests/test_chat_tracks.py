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
