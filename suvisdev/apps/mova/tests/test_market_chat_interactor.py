from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest  # noqa: E402
from mova.app.use_cases.market_chat_interactor import (  # noqa: E402
    ChatInteractor,
    _GENERAL_CHAT_SYSTEM_PROMPT,
)
from ontology.app.dtos.mycroft_dto import MycroftAnswerDto  # noqa: E402


def _build_interactor(*, classifier_destination: str) -> tuple[ChatInteractor, AsyncMock, AsyncMock]:
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


if __name__ == "__main__":
    unittest.main()
