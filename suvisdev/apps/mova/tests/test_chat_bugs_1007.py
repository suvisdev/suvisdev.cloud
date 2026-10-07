"""2026-10-07 추천 문구 실측에서 드러난 채팅 버그 — 운영에서 나온 발화 그대로 고정한다.

1) 이해 모델이 발화에 없는 제목을 지어냄 → 근거 없는 제목은 버린다(같은 유형 3건)
2) "이번 주 박스오피스 순위"가 잡담 → 예매(상영작 안내)로
3) "지금 극장에서 볼 만한 영화"가 지어낸 제목으로 예매 → 제목 없이 상영작 안내로
4) "공포는 싫고 긴장감 있는 영화"에 공포물 → 싫다고 한 장르 제외
5) "인터스텔라 같은 영화"에 인터스텔라 자신 → 유사작 경로(자기 자신 제외)
6) mova 리뷰 0건인데 "별점 0(리뷰 3건)" → 프롬프트·코드 가드
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest  # noqa: E402
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema  # noqa: E402
from mova.app.dtos.chat_understanding_dto import ChatUnderstanding, VerifiedSlots  # noqa: E402
from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto  # noqa: E402
from mova.app.use_cases.chat_orchestrator import ChatOrchestrator, _title_grounded  # noqa: E402
from mova.app.use_cases.market_chat_booking_interactor import (  # noqa: E402
    _DISCOVERY_PATTERN,
    BookingAssistService,
)
from mova.app.use_cases.market_chat_evaluation_interactor import (  # noqa: E402
    MovieEvaluationService,
    strip_unbacked_rating,
)
from mova.app.use_cases.market_chat_interactor import (  # noqa: E402
    _BOOKING_LEXICON,
    _RECOMMEND_WORD,
    ChatInteractor,
)
from mova.domain.value_objects.genre_exclusion import (  # noqa: E402
    excluded_genres,
    has_excluded_genre,
)


def _item(mid: int, title: str, genres: str = "") -> MovaSearchItemSchema:
    return MovaSearchItemSchema(
        id=str(mid),
        title=title,
        year="2020",
        rating=0.0,
        poster="",
        match_type="semantic",
        genres=genres,
    )


class TitleGroundingTests(unittest.IsolatedAsyncioTestCase):
    """1) 모델이 다른 제목을 골랐을 때 — 카탈로그에 실재해도 발화 근거가 없으면 버린다."""

    def _orch(self, u: ChatUnderstanding, items: list[MovaSearchItemSchema]) -> ChatOrchestrator:
        port = AsyncMock()
        port.understand.return_value = u
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = items
        return ChatOrchestrator(
            port, repo, booking_lexicon=_BOOKING_LEXICON, recommend_word=_RECOMMEND_WORD
        )

    async def test_hallucinated_titles_from_production_are_dropped(self) -> None:
        for message, title in [
            ("지금 극장에서 볼 만한 영화", "어벤져스: 엔드게임"),
            ("공포는 싫고 긴장감 있는 영화", "인셉션"),
            ("인터스텔라 같은 영화 추천", "아르테미스"),
            ("마블 이후에 볼 슈퍼히어로 영화", "어벤져스: 엔드게임"),
        ]:
            orch = self._orch(ChatUnderstanding(intent="recommend", title=title), [_item(1, title)])
            slots = await orch.plan(message, [], trace_id="t")
            assert slots is not None
            self.assertIsNone(slots.title_text, message)
            self.assertIsNone(slots.movie, message)

    async def test_grounded_titles_are_kept(self) -> None:
        cases = [
            ("엔드게임 예매해줘", [], "어벤져스: 엔드게임"),  # 정식 제목의 일부만 씀
            ("인샙션 어때?", [], "인셉션"),  # 한 글자 오타
            (
                "그거 군자에서 예매해줘",
                [{"role": "assistant", "content": "『인턴』은 리뷰가 좋아요."}],
                "인턴",
            ),  # 직전 대화에서 이어받기
        ]
        for message, history, title in cases:
            orch = self._orch(ChatUnderstanding(intent="booking", title=title), [_item(1, title)])
            slots = await orch.plan(message, history, trace_id="t")
            assert slots is not None
            self.assertEqual(slots.title_text, title, message)
            self.assertEqual(slots.movie.title if slots.movie else None, title, message)

    def test_short_tokens_need_exact_match(self) -> None:
        self.assertFalse(_title_grounded("곡성", "곡식 영화 추천", []))
        self.assertTrue(_title_grounded("곡성", "곡성 어때", []))


class BoxOfficeRoutingTests(unittest.IsolatedAsyncioTestCase):
    """2)·3) 제목 없는 상영작 질문은 예매 트랙의 상영작 안내로."""

    async def test_box_office_question_overrides_general_intent(self) -> None:
        port = AsyncMock()
        port.understand.return_value = ChatUnderstanding(intent="general")
        orch = ChatOrchestrator(
            port, AsyncMock(), booking_lexicon=_BOOKING_LEXICON, recommend_word=_RECOMMEND_WORD
        )
        slots = await orch.plan("이번 주 박스오피스 순위", [], trace_id="t")
        assert slots is not None
        self.assertEqual(slots.intent, "booking")

    async def test_untitled_showing_questions_list_box_office(self) -> None:
        box_office = AsyncMock()
        box_office.fetch_box_office.return_value = [
            BoxOfficeEntryDto(rank=1, movie_cd="1", title="극장판 A", open_year=2026),
            BoxOfficeEntryDto(rank=2, movie_cd="2", title="B", open_year=2026),
        ]
        svc = BookingAssistService(
            repository=AsyncMock(), movies=AsyncMock(), box_office=box_office, theaters=AsyncMock()
        )
        for message in ["이번 주 박스오피스 순위", "지금 극장에서 볼 만한 영화"]:
            result = await svc.assist_slots(
                message=message, title_text=None, verified_title=None, region=None, trace_id="t"
            )
            self.assertIn("극장판 A / B", result.reply, message)

    def test_legacy_title_path_not_hijacked(self) -> None:
        # 레거시 assist는 제목 해석 전에 _DISCOVERY_PATTERN을 본다 — "볼 만해"가 제목을 가리면 안 된다
        self.assertIsNone(_DISCOVERY_PATTERN.search("인턴 극장에서 볼 만해?"))


class GenreExclusionTests(unittest.TestCase):
    """4) 싫다고 한 장르는 검색어·후보에서 뺀다."""

    def test_parse(self) -> None:
        cases = {
            "공포는 싫고 긴장감 있는 영화": ({"공포"}, "긴장감 있는 영화"),
            "로맨스 말고 설레는 영화": ({"로맨스"}, "설레는 영화"),
            "호러물은 별로고 스릴러 추천": ({"공포"}, "스릴러 추천"),
            "애니 빼고 가족 영화": ({"애니메이션"}, "가족 영화"),
            "sf 말고 액션": ({"SF"}, "액션"),
        }
        for message, (genres, query) in cases.items():
            self.assertEqual(excluded_genres(message), (frozenset(genres), query), message)

    def test_plain_requests_untouched(self) -> None:
        for message in ["공포 영화 추천해줘", "싫은 영화 없어", "긴장감 있는 영화"]:
            self.assertEqual(excluded_genres(message), (frozenset(), message))

    def test_has_excluded_genre(self) -> None:
        ex = frozenset({"공포"})
        self.assertTrue(has_excluded_genre("공포, 스릴러", ex))
        self.assertFalse(has_excluded_genre("스릴러, 미스터리", ex))
        self.assertFalse(has_excluded_genre("", ex))  # 장르를 모르면 남긴다


def _interactor(slots: VerifiedSlots) -> ChatInteractor:
    repo = AsyncMock()
    repo.save_chat.return_value = 11
    repo.find_movie_titled_in_text.return_value = None
    orch = AsyncMock()
    orch.plan.return_value = slots
    return ChatInteractor(
        repository=repo,
        recommender=AsyncMock(),
        preferences=AsyncMock(),
        hub_rag=AsyncMock(),
        classifier=AsyncMock(),
        general=AsyncMock(),
        evaluation=AsyncMock(),
        booking=AsyncMock(),
        orchestrator=orch,
    )


def _recommend_slots() -> VerifiedSlots:
    return VerifiedSlots(
        intent="recommend",
        title_text=None,
        movie=None,
        region=None,
        time=None,
        chain=None,
        followup=False,
    )


class SimilarDispatchTests(unittest.IsolatedAsyncioTestCase):
    """5) "OO 같은 영화"는 유사작 경로(find_similar_movies가 자기 자신을 뺀다)."""

    async def test_similar_cue_goes_to_personal_recommend(self) -> None:
        interactor = _interactor(_recommend_slots())
        interactor._reply_personal_recommend = AsyncMock(return_value="similar")  # type: ignore[method-assign]
        interactor._reply_recommend = AsyncMock(return_value="recommend")  # type: ignore[method-assign]
        await interactor.chat(MovaChatRequest(message="인터스텔라 같은 영화 추천"))
        interactor._reply_personal_recommend.assert_awaited_once()
        self.assertEqual(
            interactor._reply_personal_recommend.await_args.kwargs["seed_title"], "인터스텔라"
        )
        interactor._reply_recommend.assert_not_awaited()

    async def test_conditional_request_stays_recommend(self) -> None:
        interactor = _interactor(_recommend_slots())
        interactor._reply_personal_recommend = AsyncMock()  # type: ignore[method-assign]
        interactor._reply_recommend = AsyncMock(return_value="recommend")  # type: ignore[method-assign]
        await interactor.chat(MovaChatRequest(message="공포는 싫고 긴장감 있는 영화"))
        interactor._reply_recommend.assert_awaited_once()
        interactor._reply_personal_recommend.assert_not_awaited()


class UnbackedRatingTests(unittest.IsolatedAsyncioTestCase):
    """6) mova 리뷰가 없으면 별점을 말하지 않는다 — 운영에서 나온 문장 그대로."""

    def test_strip_production_sentences(self) -> None:
        cases = {
            "호평받습니다. 별점 0(리뷰 3건, 참고용)으로, 치밀한 설계를 즐기는 관객에게 추천합니다.": (
                "호평받습니다. 치밀한 설계를 즐기는 관객에게 추천합니다."
            ),
            "뮤지컬 영화입니다. 별점 2.5(리뷰 3건, 참고용)인 이 작품은 호평이 있습니다.": (
                "뮤지컬 영화입니다. 이 작품은 호평이 있습니다."
            ),
            "의견도 존재합니다. 별점 0(리뷰 0건, 참고용). 스릴러 팬에게 추천합니다.": (
                "의견도 존재합니다. 스릴러 팬에게 추천합니다."
            ),
        }
        for raw, want in cases.items():
            self.assertEqual(strip_unbacked_rating(raw), want)

    async def _compose(self, *, count: int, avg: float | None, llm_text: str) -> tuple[str, str]:
        general = AsyncMock()
        general.ask.return_value = MagicMock(text=llm_text)
        svc = MovieEvaluationService(
            repository=AsyncMock(), movies=AsyncMock(), reviews=AsyncMock(), general=general
        )
        reply = await svc._compose_reply(
            title="인셉션",
            year=2010,
            genres=["SF"],
            synopsis="꿈",
            aggregate_count=count,
            aggregate_avg=avg,
            excerpts=[],
            external=["good", "great", "nice"],
        )
        return reply, general.ask.await_args.args[0].question

    async def test_no_reviews_tells_model_and_strips_leak(self) -> None:
        reply, data = await self._compose(
            count=0,
            avg=None,
            llm_text="꿈 이야기입니다. 별점 0(리뷰 3건, 참고용)으로, SF 팬에게 추천합니다.",
        )
        self.assertIn("[mova 리뷰] 없음", data)
        self.assertNotIn("표본 부족", data)
        self.assertEqual(reply, "꿈 이야기입니다. SF 팬에게 추천합니다.")

    async def test_real_rating_is_kept(self) -> None:
        text = "꿈 이야기입니다. 별점 4.5(리뷰 5건)로 호평입니다."
        reply, data = await self._compose(count=5, avg=4.5, llm_text=text)
        self.assertIn("평균 별점 4.5", data)
        self.assertEqual(reply, text)
