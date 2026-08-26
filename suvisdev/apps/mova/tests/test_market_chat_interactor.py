from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.schemas.market_chat_schema import (  # noqa: E402
    MovaChatRecommendationSchema,
    MovaChatRequest,
)
from mova.app.use_cases.market_chat_interactor import (  # noqa: E402
    _GENERAL_CHAT_SYSTEM_PROMPT,
    ChatInteractor,
)
from ontology.app.dtos.mycroft_dto import MycroftAnswerDto  # noqa: E402


def _build_interactor(
    *, classifier_destination: str
) -> tuple[ChatInteractor, AsyncMock, AsyncMock]:
    repo = AsyncMock()
    repo.save_chat.return_value = 1
    classifier = AsyncMock()
    classifier.classify.return_value = (classifier_destination, [])
    general = AsyncMock()
    general.ask.return_value = MycroftAnswerDto(text="답변입니다.")

    interactor = ChatInteractor(
        repository=repo,
        recommender=AsyncMock(),
        preferences=AsyncMock(),
        hub_rag=AsyncMock(),
        classifier=classifier,
        general=general,
    )
    return interactor, repo, general


class ChatInteractorGeneralRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_destination_calls_mycroft_with_system_prompt(self) -> None:
        interactor, _repo, general = _build_interactor(classifier_destination="general")
        request = MovaChatRequest(message="오늘 기분 어때?", history=[])

        response = await interactor.chat(request)

        general.ask.assert_awaited_once()
        command = general.ask.await_args.args[0]
        self.assertEqual(command.system, _GENERAL_CHAT_SYSTEM_PROMPT)
        self.assertTrue(command.system)
        self.assertEqual(response.reply, "답변입니다.")
        self.assertEqual(response.recommendations, [])

    async def test_general_includes_recent_history_in_question(self) -> None:
        """불만·후속 발화가 맥락 없이 인사말로 답변되던 것 방지(2026-08-26) —
        히스토리가 있으면 [이전 대화] 블록으로 질문에 인라인된다."""
        interactor, _repo, general = _build_interactor(classifier_destination="general")
        request = MovaChatRequest(
            message="똑같은 말 반복하지마",
            history=[
                {"role": "user", "content": "코미디 추천해줘"},
                {"role": "assistant", "content": "명작 코미디를 추천해 드릴게요."},
            ],
        )

        await interactor.chat(request)

        command = general.ask.await_args.args[0]
        self.assertIn("[이전 대화]", command.question)
        self.assertIn("코미디 추천해줘", command.question)
        self.assertIn("[현재 발화]\n똑같은 말 반복하지마", command.question)

    async def test_general_without_history_sends_message_as_is(self) -> None:
        interactor, _repo, general = _build_interactor(classifier_destination="general")
        request = MovaChatRequest(message="안녕", history=[])

        await interactor.chat(request)

        self.assertEqual(general.ask.await_args.args[0].question, "안녕")

    async def test_crud_destination_also_calls_mycroft_with_system_prompt(self) -> None:
        """ea167b5에서 crud도 general과 동일 처리로 통합된 구조를 유지하는지 확인."""
        interactor, _repo, general = _build_interactor(classifier_destination="crud")
        request = MovaChatRequest(message="이 리뷰 삭제해줘", history=[])

        await interactor.chat(request)

        general.ask.assert_awaited_once()
        command = general.ask.await_args.args[0]
        self.assertEqual(command.system, _GENERAL_CHAT_SYSTEM_PROMPT)


class ChatInteractorSearchTagCatalogTests(unittest.IsolatedAsyncioTestCase):
    """rag 경로에서 search_filters.must/similar_to의 actors가 search_tag_catalog로
    전달되는지 확인(2026-08-06 search_tag_catalog 개선 — 배우 매칭 지원)."""

    def _build(
        self,
        *,
        must_actors: list[str],
        similar_actors: list[str] | None = None,
        countries: list[str] | None = None,
        years: tuple[int | None, int | None] = (None, None),
    ) -> tuple[ChatInteractor, AsyncMock]:
        repo = AsyncMock()
        repo.save_chat.return_value = 1
        repo.search_tag_catalog.return_value = []
        classifier = AsyncMock()
        classifier.classify.return_value = ("rag", [])
        hub_rag = AsyncMock()
        hub_rag.search_movies.return_value = []

        recommender = AsyncMock()
        recommender.extract_intent = Mock(
            return_value={
                "refined_query": "테스트",
                "keywords": ["코미디", "전지현"],
                "intent_type": "filter_and",
                "search_filters": {
                    "must": {
                        "actors": must_actors,
                        "genres": ["코미디"],
                        "keywords": [],
                        "countries": countries or [],
                    },
                    "similar_to": {"actors": similar_actors or []},
                    "year_min": years[0],
                    "year_max": years[1],
                },
            }
        )
        recommender.generate_recommendation.return_value = ("답변입니다.", [])

        interactor = ChatInteractor(
            repository=repo,
            recommender=recommender,
            preferences=AsyncMock(),
            hub_rag=hub_rag,
            classifier=classifier,
            general=AsyncMock(),
        )
        return interactor, repo

    async def test_must_actors_forwarded_to_search_tag_catalog(self) -> None:
        interactor, repo = self._build(must_actors=["전지현"])
        request = MovaChatRequest(message="전지현 나오는 코미디", history=[])

        await interactor.chat(request)

        repo.search_tag_catalog.assert_awaited_once()
        args, kwargs = repo.search_tag_catalog.await_args
        self.assertEqual(args[0], ["코미디", "전지현"])
        self.assertEqual(kwargs["limit"], 16)
        self.assertEqual(kwargs["actor_names"], ["전지현"])

    async def test_similar_to_actors_also_forwarded(self) -> None:
        interactor, repo = self._build(must_actors=[], similar_actors=["송강호"])
        request = MovaChatRequest(message="송강호랑 비슷한 배우 영화", history=[])

        await interactor.chat(request)

        kwargs = repo.search_tag_catalog.await_args.kwargs
        self.assertEqual(kwargs["actor_names"], ["송강호"])

    async def test_countries_and_year_range_forwarded(self) -> None:
        """골든셋 #9 — 국가·연도가 후보 쿼리까지 전달돼야 한다(2026-08-07)."""
        interactor, repo = self._build(must_actors=[], countries=["KR"], years=(2020, 2029))
        request = MovaChatRequest(message="2020년대 한국 액션", history=[])

        await interactor.chat(request)

        kwargs = repo.search_tag_catalog.await_args.kwargs
        self.assertEqual(kwargs["countries"], ["KR"])
        self.assertEqual(kwargs["year_min"], 2020)
        self.assertEqual(kwargs["year_max"], 2029)


class ChatInteractorHistoryForwardTests(unittest.IsolatedAsyncioTestCase):
    """extract_intent에 대화 history가 함께 전달되는지 확인
    — 후속 발화가 이전 조건을 삼키는 문제 대응(2026-08-14)."""

    async def test_history_passed_to_extract_intent(self) -> None:
        repo = AsyncMock()
        repo.save_chat.return_value = 1
        repo.search_tag_catalog.return_value = []
        classifier = AsyncMock()
        classifier.classify.return_value = ("rag", [])
        hub_rag = AsyncMock()
        hub_rag.search_movies.return_value = []

        recommender = AsyncMock()
        recommender.extract_intent = Mock(
            return_value={
                "refined_query": "테스트",
                "keywords": [],
                "intent_type": "mood",
                "search_filters": {
                    "must": {"actors": [], "genres": [], "keywords": [], "countries": []},
                    "similar_to": {"actors": []},
                    "year_min": None,
                    "year_max": None,
                },
            }
        )
        recommender.generate_recommendation.return_value = ("답변", [])

        interactor = ChatInteractor(
            repository=repo,
            recommender=recommender,
            preferences=AsyncMock(),
            hub_rag=hub_rag,
            classifier=classifier,
            general=AsyncMock(),
        )
        history = [
            {"role": "user", "content": "코미디 영화 추천해줘"},
            {"role": "assistant", "content": "골라봤어요."},
        ]
        await interactor.chat(MovaChatRequest(message="최근영화로", history=history))

        recommender.extract_intent.assert_called_once()
        args, kwargs = recommender.extract_intent.call_args
        self.assertEqual(args[0], "최근영화로")
        # history는 두 번째 positional 또는 kw로 전달되어야 함
        passed_history = args[1] if len(args) > 1 else kwargs.get("history")
        self.assertEqual(passed_history, history)


class ChatInteractorTasteRerankTests(unittest.IsolatedAsyncioTestCase):
    """taste vector cosine 재정렬 — 5개 어댑터 공통 경로라 인터랙터에서 검증.

    (a) taste vector 있음 → cosine 순으로 재정렬(순서 뒤바뀜 실측)
    (b) taste vector 없음(리뷰 없는 유저) → LLM 원 순서 유지, movies port 미호출
    (c) user_id None(비로그인) → taste·movies port 둘 다 미호출, LLM 원 순서 유지
    """

    def _rec(self, movie_id: int, title: str) -> MovaChatRecommendationSchema:
        return MovaChatRecommendationSchema(
            id=f"tmdb-{movie_id}",
            movie_id=movie_id,
            title=title,
            poster="",
            synopsis="",
            platform=None,
            hook="",
        )

    def _build(
        self, *, recs: list[MovaChatRecommendationSchema], with_taste_ports: bool = True
    ) -> tuple[ChatInteractor, AsyncMock, AsyncMock]:
        repo = AsyncMock()
        repo.save_chat.return_value = 1
        repo.search_tag_catalog.return_value = []
        classifier = AsyncMock()
        classifier.classify.return_value = ("rag", [])
        hub_rag = AsyncMock()
        hub_rag.search_movies.return_value = []
        recommender = AsyncMock()
        recommender.extract_intent = Mock(
            return_value={
                "refined_query": "테스트",
                "keywords": [],
                "intent_type": "mood",
                "search_filters": {
                    "must": {"actors": [], "genres": [], "keywords": [], "countries": []},
                    "similar_to": {"actors": []},
                    "year_min": None,
                    "year_max": None,
                },
            }
        )
        recommender.generate_recommendation.return_value = ("답변", recs)

        taste_repo = AsyncMock() if with_taste_ports else None
        movies_repo = AsyncMock() if with_taste_ports else None

        interactor = ChatInteractor(
            repository=repo,
            recommender=recommender,
            preferences=AsyncMock(),
            hub_rag=hub_rag,
            classifier=classifier,
            general=AsyncMock(),
            movies=movies_repo,
            taste_vectors=taste_repo,
        )
        return interactor, taste_repo, movies_repo

    async def test_taste_vector_present_reorders_recs(self) -> None:
        # 3편: taste vector와 정확히 일치하는 두 번째 rec을 앞으로 보내야 함.
        recs = [
            self._rec(101, "A"),
            self._rec(202, "B (best match)"),
            self._rec(303, "C"),
        ]
        interactor, taste_repo, movies_repo = self._build(recs=recs)
        taste_repo.get_taste_vector.return_value = [1.0, 0.0, 0.0]
        movies_repo.list_embeddings_by_ids.return_value = {
            101: [0.5, 0.5, 0.0],  # cosine ≈ 0.707
            202: [1.0, 0.0, 0.0],  # cosine = 1.0
            303: [0.0, 1.0, 0.0],  # cosine = 0.0
        }

        response = await interactor.chat(MovaChatRequest(message="추천", history=[], user_id=42))

        # movie_id 순서: 202(가장 유사) → 101 → 303
        actual = [r.movie_id for r in response.recommendations]
        self.assertEqual(actual, [202, 101, 303])
        # save_picks 순서도 재정렬 결과와 일치해야 저장·화면이 어긋나지 않음
        picks_kwargs = interactor._repo.save_picks.await_args.kwargs
        saved_movie_ids = [r.movie_id for r in picks_kwargs["recommendations"]]
        self.assertEqual(saved_movie_ids, [202, 101, 303])

    async def test_taste_vector_missing_keeps_original_order(self) -> None:
        # 로그인 유저지만 리뷰 0건이라 taste vector = None → 재정렬 스킵.
        recs = [self._rec(101, "A"), self._rec(202, "B"), self._rec(303, "C")]
        interactor, taste_repo, movies_repo = self._build(recs=recs)
        taste_repo.get_taste_vector.return_value = None

        response = await interactor.chat(MovaChatRequest(message="추천", history=[], user_id=42))

        self.assertEqual([r.movie_id for r in response.recommendations], [101, 202, 303])
        # taste vector가 없으면 movies embeddings 페치 자체를 건너뜀
        movies_repo.list_embeddings_by_ids.assert_not_awaited()

    async def test_anonymous_user_skips_taste_lookup(self) -> None:
        # 비로그인: taste·movies port가 주입돼 있어도 호출조차 안 함.
        recs = [self._rec(101, "A"), self._rec(202, "B"), self._rec(303, "C")]
        interactor, taste_repo, movies_repo = self._build(recs=recs)

        response = await interactor.chat(MovaChatRequest(message="추천", history=[]))

        self.assertEqual([r.movie_id for r in response.recommendations], [101, 202, 303])
        taste_repo.get_taste_vector.assert_not_awaited()
        movies_repo.list_embeddings_by_ids.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
