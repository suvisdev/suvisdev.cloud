from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest  # noqa: E402
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema  # noqa: E402
from mova.app.dtos.market_conversations_dto import (  # noqa: E402
    ConversationDetailDto,
    ConversationMessageDto,
    ConversationSummaryDto,
)
from mova.app.ports.output.market_conversations_errors import (  # noqa: E402
    ConversationForbiddenError,
    ConversationNotFoundError,
)
from mova.app.use_cases.market_chat_interactor import ChatInteractor  # noqa: E402
from mova.app.use_cases.market_conversations_interactor import (  # noqa: E402
    ConversationsInteractor,
)


class ConversationsInteractorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repo = AsyncMock()
        self.interactor = ConversationsInteractor(repository=self.repo)

    async def test_list_mine_returns_repo_result(self) -> None:
        self.repo.list_by_user.return_value = [
            ConversationSummaryDto(
                id=1, title="영화 추천 얘기", updated_at=datetime.now(UTC), message_count=4
            )
        ]

        result = await self.interactor.list_mine(user_id=42)

        self.repo.list_by_user.assert_awaited_once_with(42)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "영화 추천 얘기")

    async def test_get_mine_raises_not_found_when_missing(self) -> None:
        self.repo.get_owner_id.return_value = None

        with self.assertRaises(ConversationNotFoundError):
            await self.interactor.get_mine(conversation_id=99, user_id=42)

        self.repo.get_detail.assert_not_called()

    async def test_get_mine_raises_forbidden_when_wrong_owner(self) -> None:
        self.repo.get_owner_id.return_value = 7  # 다른 사람 소유

        with self.assertRaises(ConversationForbiddenError):
            await self.interactor.get_mine(conversation_id=99, user_id=42)

    async def test_get_mine_returns_detail_when_owner_matches(self) -> None:
        now = datetime.now(UTC)
        self.repo.get_owner_id.return_value = 42
        self.repo.get_detail.return_value = ConversationDetailDto(
            id=99,
            title="스릴러 얘기",
            created_at=now,
            updated_at=now,
            messages=[
                ConversationMessageDto(
                    id=1, role="user", content="스릴러 추천", meta={}, created_at=now
                ),
                ConversationMessageDto(
                    id=2, role="assistant", content="세븐 어때요?", meta={}, created_at=now
                ),
            ],
        )

        detail = await self.interactor.get_mine(conversation_id=99, user_id=42)

        self.assertEqual(detail.title, "스릴러 얘기")
        self.assertEqual(len(detail.messages), 2)

    async def test_delete_mine_calls_repo_when_owner_matches(self) -> None:
        self.repo.get_owner_id.return_value = 42

        await self.interactor.delete_mine(conversation_id=99, user_id=42)

        self.repo.delete.assert_awaited_once_with(99)

    async def test_delete_mine_forbidden_when_wrong_owner(self) -> None:
        self.repo.get_owner_id.return_value = 7

        with self.assertRaises(ConversationForbiddenError):
            await self.interactor.delete_mine(conversation_id=99, user_id=42)

        self.repo.delete.assert_not_called()


class ChatInteractorDedupTests(unittest.IsolatedAsyncioTestCase):
    """대화 스레드의 이전 추천을 제외하는 필터 검증."""

    @staticmethod
    def _item(i: int) -> MovaSearchItemSchema:
        return MovaSearchItemSchema(
            id=f"tmdb-{i}", title=f"영화{i}", year="", rating=0.0, poster="", match_type="tag"
        )

    async def _run_chat(
        self, *, already_shown: set[str], wider_catalog: list | None = None
    ) -> tuple[list, list]:
        """catalog에 tmdb-1,2,3, LLM은 catalog 전체를 그대로 픽. 이미 소개한 슬러그는
        후보에서 제거돼야 하고, LLM이 실수로 되돌려줘도 최종 응답에서 필터돼야 한다.
        wider_catalog가 주어지면 두 번째 search_tag_catalog(풀 확장 재검색)가 그걸 돌려준다."""
        classifier = AsyncMock()
        classifier.classify.return_value = ("rag", [])
        chat_repo = AsyncMock()
        chat_repo.save_chat.return_value = 42
        chat_repo.get_recent_intents_by_user.return_value = []
        first_catalog = [self._item(i) for i in (1, 2, 3)]
        if wider_catalog is None:
            chat_repo.search_tag_catalog.return_value = first_catalog
        else:
            chat_repo.search_tag_catalog.side_effect = [first_catalog, wider_catalog]
        preferences = AsyncMock()
        preferences.get_preferences.return_value = type(
            "P", (), {"nickname": "u", "preferred_genres": []}
        )()
        hub_rag = AsyncMock()
        hub_rag.search_movies.return_value = []  # 태그 폴백 경로로

        # LLM은 받은 catalog(필터 후)를 그대로 돌려주도록 mock
        captured: dict = {}

        async def gen_rec(*, tag_catalog, **_kwargs):
            captured["catalog_seen"] = list(tag_catalog)
            from mova.adapter.inbound.api.schemas.market_chat_schema import (
                MovaChatRecommendationSchema,
            )

            recs = [
                MovaChatRecommendationSchema(
                    id=c.id,
                    movie_id=None,
                    title=c.title,
                    year="",
                    poster="",
                    synopsis="",
                    platform=None,
                    hook="",
                )
                for c in tag_catalog
            ]
            return ("추천합니다.", recs)

        llm = Mock()  # extract_intent가 sync라 AsyncMock 대신 Mock
        llm.extract_intent.return_value = {
            "refined_query": "다른 것도",
            "keywords": [],
            "intent_type": "mood",
            "search_filters": {},
        }
        llm.generate_recommendation = AsyncMock(side_effect=gen_rec)

        conversations = AsyncMock()
        conversations.get_recent_recommendation_slugs.return_value = already_shown
        conversations.get_owner_id.return_value = 7  # 소유 통과

        interactor = ChatInteractor(
            repository=chat_repo,
            recommender=llm,
            preferences=preferences,
            hub_rag=hub_rag,
            classifier=classifier,
            general=AsyncMock(),
            conversations=conversations,
        )
        req = MovaChatRequest(message="다른 것도", history=[], user_id=7, conversation_id=99)
        dto = await interactor.chat(req)
        return captured["catalog_seen"], dto.recommendations

    async def test_previously_shown_movies_are_excluded_from_llm_and_response(self) -> None:
        catalog_seen, final = await self._run_chat(already_shown={"tmdb-1", "tmdb-2"})
        seen_ids = [c.id for c in catalog_seen]
        final_ids = [r.id for r in final]
        self.assertEqual(seen_ids, ["tmdb-3"], "LLM 후보에서 이미 소개한 영화가 빠져야 함")
        self.assertEqual(final_ids, ["tmdb-3"], "최종 응답에도 이미 소개한 영화가 없어야 함")

    async def test_empty_already_shown_keeps_all_candidates(self) -> None:
        catalog_seen, final = await self._run_chat(already_shown=set())
        self.assertEqual([c.id for c in catalog_seen], ["tmdb-1", "tmdb-2", "tmdb-3"])
        self.assertEqual([r.id for r in final], ["tmdb-1", "tmdb-2", "tmdb-3"])

    async def test_all_candidates_shown_falls_back_to_full_catalog(self) -> None:
        """필터 후 후보가 0이면 원본 유지(사용자에게 빈 응답 대신 뭔가라도 주기 위함).
        최종 응답에서만 완전 제거되어 실제론 0카드가 나감."""
        catalog_seen, final = await self._run_chat(already_shown={"tmdb-1", "tmdb-2", "tmdb-3"})
        self.assertEqual([c.id for c in catalog_seen], ["tmdb-1", "tmdb-2", "tmdb-3"])
        self.assertEqual([r.id for r in final], [])

    async def test_dedup_exhausted_widens_pool_and_serves_new_candidates(self) -> None:
        """dedup 소진 대안 행동(2026-08-26) — 첫 16편이 전부 소개된 상태면 풀을
        넓혀 재검색하고, 거기서 아직 안 보여준 영화만 후보로 쓴다."""
        wider = [self._item(i) for i in (1, 2, 3, 4, 5, 6)]
        catalog_seen, final = await self._run_chat(
            already_shown={"tmdb-1", "tmdb-2", "tmdb-3"}, wider_catalog=wider
        )
        self.assertEqual([c.id for c in catalog_seen], ["tmdb-4", "tmdb-5", "tmdb-6"])
        self.assertEqual([r.id for r in final], ["tmdb-4", "tmdb-5", "tmdb-6"])

    async def test_zero_recs_replaces_reply_with_honest_message(self) -> None:
        """recs가 0건이 되면 reply를 '추천할 영화가 없어요' 계열로 대체.
        LLM이 '추천해 드릴게요' 같은 문구를 남겼는데 카드가 없으면 사용자가
        혼란을 느끼므로 정직하게 안내."""
        # 이미 소개한 케이스: '이 대화에서'가 문구에 포함
        _catalog, final = await self._run_chat(already_shown={"tmdb-1", "tmdb-2", "tmdb-3"})
        self.assertEqual(final, [])
        # dto의 reply는 self._run_chat이 노출 안 하니 별도 검증 필요 —
        # 여기선 recs=0인 시나리오가 예외 없이 통과하는지만 확인(문구는 아래 별도 테스트).

    async def test_zero_recs_reply_content_when_already_shown_all(self) -> None:
        classifier = AsyncMock()
        classifier.classify.return_value = ("rag", [])
        chat_repo = AsyncMock()
        chat_repo.save_chat.return_value = 42
        chat_repo.get_recent_intents_by_user.return_value = []
        chat_repo.search_tag_catalog.return_value = [
            MovaSearchItemSchema(
                id="tmdb-1", title="a", year="", rating=0.0, poster="", match_type="tag"
            )
        ]
        preferences = AsyncMock()
        preferences.get_preferences.return_value = type(
            "P", (), {"nickname": "u", "preferred_genres": []}
        )()
        hub_rag = AsyncMock()
        hub_rag.search_movies.return_value = []
        llm = Mock()
        llm.extract_intent.return_value = {
            "refined_query": "다른것",
            "keywords": [],
            "intent_type": "mood",
            "search_filters": {},
        }
        # LLM은 소개한 것을 그대로 다시 돌려주는 시나리오(전량 필터 예정)
        from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRecommendationSchema

        llm.generate_recommendation = AsyncMock(
            return_value=(
                "취향에 맞춰 엄선한 명작 영화들을 추천해 드릴게요.",
                [
                    MovaChatRecommendationSchema(
                        id="tmdb-1",
                        movie_id=None,
                        title="a",
                        year="",
                        poster="",
                        synopsis="",
                        platform=None,
                        hook="",
                    )
                ],
            )
        )
        conversations = AsyncMock()
        conversations.get_recent_recommendation_slugs.return_value = {"tmdb-1"}
        conversations.get_owner_id.return_value = 7

        interactor = ChatInteractor(
            repository=chat_repo,
            recommender=llm,
            preferences=preferences,
            hub_rag=hub_rag,
            classifier=classifier,
            general=AsyncMock(),
            conversations=conversations,
        )
        req = MovaChatRequest(message="다른것도", history=[], user_id=7, conversation_id=99)
        # 안내 문구는 변형 3종 중 랜덤 pick — 첫 변형으로 고정해 결정적으로 검증한다.
        with unittest.mock.patch("random.choice", lambda pool: pool[0]):
            dto = await interactor.chat(req)

        self.assertEqual(dto.recommendations, [])
        self.assertIn("이 대화에서 아직 소개하지 않은", dto.reply)


if __name__ == "__main__":
    unittest.main()
