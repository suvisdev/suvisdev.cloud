"""오케스트레이터 층(2026-09-27) — 이해(LLM 출력 정제)·검증(카탈로그)·디스패치."""

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
from mova.adapter.outbound.llm.exaone_chat_understanding_adapter import (  # noqa: E402
    ExaoneChatUnderstandingAdapter,
    parse_understanding,
)
from mova.app.dtos.chat_understanding_dto import ChatUnderstanding, VerifiedSlots  # noqa: E402
from mova.app.ports.output.chat_understanding_port import ChatUnderstandingError  # noqa: E402
from mova.app.use_cases.chat_orchestrator import ChatOrchestrator  # noqa: E402
from mova.app.use_cases.market_chat_booking_interactor import BookingResult  # noqa: E402
from mova.app.use_cases.market_chat_interactor import (  # noqa: E402
    _BOOKING_LEXICON,
    _RECOMMEND_WORD,
    ChatInteractor,
)


def _item(mid: int, title: str, year: str = "2026") -> MovaSearchItemSchema:
    return MovaSearchItemSchema(
        id=str(mid), title=title, year=year, rating=0.0, poster="", match_type="title"
    )


class ParseUnderstandingTests(unittest.TestCase):
    def test_clean_values_and_schema_echo_dropped(self) -> None:
        # 2.4B 실측 출력: 스키마 문구·"null" 문자열·발화에 없는 체인명
        raw = '{"intent":"booking","title":"null","region":"군자","time":"시각/날짜 표현","chain":"CGV|롯데시네마|메가박스|null","followup":true}'
        u = parse_understanding(raw, "군자에서 인턴 오늘 몇 시에 볼 수 있어?")
        self.assertEqual(u.intent, "booking")
        self.assertIsNone(u.title)
        self.assertEqual(u.region, "군자")
        self.assertIsNone(u.time)
        self.assertIsNone(u.chain)
        self.assertTrue(u.followup)

    def test_chain_only_when_in_message(self) -> None:
        u = parse_understanding('{"intent":"booking","title":"인턴","chain":"CGV"}', "군자 인턴")
        self.assertIsNone(u.chain)
        u2 = parse_understanding(
            '{"intent":"booking","title":"인턴","chain":"CGV"}', "군자 CGV 인턴"
        )
        self.assertEqual(u2.chain, "CGV")

    def test_json_embedded_in_prose_and_bad_intent(self) -> None:
        u = parse_understanding(
            '결과: {"intent":"evaluate","title":"옵세션"} 입니다', "옵세션 어때"
        )
        self.assertEqual((u.intent, u.title), ("evaluate", "옵세션"))
        with self.assertRaises(ChatUnderstandingError):
            parse_understanding('{"intent":"rag"}', "x")
        with self.assertRaises(ChatUnderstandingError):
            parse_understanding("그냥 문장", "x")

    def test_nullish_korean_dropped(self) -> None:
        u = parse_understanding(
            '{"intent":"recommend","title":"없음","region":"없음"}', "코미디 추천"
        )
        self.assertIsNone(u.title)
        self.assertIsNone(u.region)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_calls_client_with_json_mode_and_history(self) -> None:
        client = MagicMock()
        client.understand_json.return_value = {
            "intent": "booking",
            "title": "인턴",
            "region": "군자",
            "followup": True,
        }
        adapter = ExaoneChatUnderstandingAdapter(client=client)
        u = await adapter.understand(
            "군자", [{"role": "assistant", "content": "『인턴』 어느 지역에서 보실 계획인가요?"}]
        )
        self.assertEqual((u.title, u.region, u.followup), ("인턴", "군자", True))
        kwargs = client.understand_json.call_args.kwargs
        self.assertEqual(kwargs["num_ctx"], 2048)
        self.assertIn("도우미: 『인턴』", client.understand_json.call_args.args[0])

    async def test_client_error_becomes_understanding_error(self) -> None:
        from core.lol.ollama_client import OllamaClientError

        client = MagicMock()
        client.understand_json.side_effect = OllamaClientError("down", status_code=503)
        with self.assertRaises(ChatUnderstandingError):
            await ExaoneChatUnderstandingAdapter(client=client).understand("안녕", [])


class OrchestratorTests(unittest.IsolatedAsyncioTestCase):
    def _orch(
        self, understanding: ChatUnderstanding | Exception, items: list[MovaSearchItemSchema]
    ):
        port = AsyncMock()
        if isinstance(understanding, Exception):
            port.understand.side_effect = understanding
        else:
            port.understand.return_value = understanding
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = items
        return ChatOrchestrator(
            port, repo, booking_lexicon=_BOOKING_LEXICON, recommend_word=_RECOMMEND_WORD
        )

    async def test_title_verified_by_exact_catalog_match(self) -> None:
        orch = self._orch(
            ChatUnderstanding(intent="booking", title="인턴", region="군자"),
            [_item(4715, "인턴"), _item(9, "인턴십")],
        )
        slots = await orch.plan("군자에서 인턴", [], trace_id="t")
        assert slots is not None
        self.assertEqual(slots.movie.id, "4715")
        self.assertEqual(slots.region, "군자")

    async def test_unknown_title_stays_text_only(self) -> None:
        orch = self._orch(ChatUnderstanding(intent="booking", title="없는영화"), [])
        slots = await orch.plan("없는영화 예매", [], trace_id="t")
        assert slots is not None
        self.assertIsNone(slots.movie)
        self.assertEqual(slots.title_text, "없는영화")

    async def test_booking_lexicon_overrides_llm_intent(self) -> None:
        orch = self._orch(ChatUnderstanding(intent="general", title="인턴"), [_item(4715, "인턴")])
        slots = await orch.plan("인턴 영화 시간표 보여줘", [], trace_id="t")
        assert slots is not None
        self.assertEqual(slots.intent, "booking")

    async def test_recommend_wording_not_overridden(self) -> None:
        orch = self._orch(ChatUnderstanding(intent="recommend"), [])
        slots = await orch.plan("영화관에서 볼만한 거 추천해줘", [], trace_id="t")
        assert slots is not None
        self.assertEqual(slots.intent, "recommend")

    async def test_understanding_failure_returns_none(self) -> None:
        orch = self._orch(ChatUnderstandingError("ollama down"), [])
        self.assertIsNone(await orch.plan("안녕", [], trace_id="t"))


class ShadowTests(unittest.IsolatedAsyncioTestCase):
    async def test_shadow_runs_in_background_and_records_diff(self) -> None:
        """섀도 모델은 응답을 막지 않고 백그라운드로 돌며, 필드별 불일치를 기록한다(2026-09-28)."""
        import asyncio

        from mova.app.use_cases import chat_orchestrator as mod

        primary = AsyncMock()
        primary.understand.return_value = ChatUnderstanding(
            intent="booking", title="인턴", region="군자"
        )
        shadow = AsyncMock()
        shadow.understand.return_value = ChatUnderstanding(
            intent="booking", title="인턴", region="군자역"
        )
        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [_item(4715, "인턴")]
        records: list[dict] = []
        orch = ChatOrchestrator(primary, repo, shadow=shadow, on_shadow=records.append)

        slots = await orch.plan("군자역에서 인턴", [], trace_id="t1")
        assert slots is not None
        self.assertEqual(slots.region, "군자")  # 응답은 주 모델 기준
        await asyncio.gather(*list(mod._shadow_tasks))

        self.assertEqual(len(records), 1)
        self.assertFalse(records[0]["match"])
        self.assertEqual(records[0]["diff"], ["region"])
        self.assertEqual(records[0]["shadow"]["region"], "군자역")

    async def test_shadow_failure_is_recorded_not_raised(self) -> None:
        import asyncio

        from mova.app.use_cases import chat_orchestrator as mod

        primary = AsyncMock()
        primary.understand.return_value = ChatUnderstanding(intent="general")
        shadow = AsyncMock()
        shadow.understand.side_effect = ChatUnderstandingError("ollama 404")
        records: list[dict] = []
        orch = ChatOrchestrator(primary, AsyncMock(), shadow=shadow, on_shadow=records.append)
        await orch.plan("안녕", [], trace_id="t2")
        await asyncio.gather(*list(mod._shadow_tasks))
        self.assertIn("404", records[0]["shadow_error"])

    async def test_no_shadow_by_default(self) -> None:
        from mova.app.use_cases import chat_orchestrator as mod

        primary = AsyncMock()
        primary.understand.return_value = ChatUnderstanding(intent="general")
        await ChatOrchestrator(primary, AsyncMock()).plan("안녕", [], trace_id="t3")
        self.assertEqual(len(mod._shadow_tasks), 0)


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    def _interactor(self, slots: VerifiedSlots | None):
        repo = AsyncMock()
        repo.save_chat.return_value = 11
        repo.find_movie_titled_in_text.return_value = None
        orch = AsyncMock()
        orch.plan.return_value = slots
        classifier = AsyncMock()
        classifier.classify.return_value = ("general", [])
        booking = AsyncMock()
        booking.assist_slots.return_value = BookingResult(
            status="ok", reply="극장 5곳", card=None, booking=None
        )
        booking.assist.return_value = BookingResult(
            status="ok", reply="legacy", card=None, booking=None
        )
        interactor = ChatInteractor(
            repository=repo,
            recommender=AsyncMock(),
            preferences=AsyncMock(),
            hub_rag=AsyncMock(),
            classifier=classifier,
            general=AsyncMock(),
            evaluation=AsyncMock(),
            booking=booking,
            orchestrator=orch,
        )
        return interactor, booking, classifier

    async def test_booking_slots_go_straight_to_region_search(self) -> None:
        slots = VerifiedSlots(
            intent="booking",
            title_text="인턴",
            movie=_item(4715, "인턴"),
            region="군자",
            time=None,
            chain=None,
            followup=False,
        )
        interactor, booking, classifier = self._interactor(slots)
        resp = await interactor.chat(
            MovaChatRequest(message="군자에서 인턴 오늘 몇 시에 볼 수 있어?")
        )
        self.assertEqual(resp.response_type, "booking")
        self.assertEqual(resp.reply, "극장 5곳")
        kwargs = booking.assist_slots.await_args.kwargs
        self.assertEqual((kwargs["verified_title"], kwargs["region"]), ("인턴", "군자"))
        classifier.classify.assert_not_awaited()

    async def test_plan_none_falls_back_to_legacy_path(self) -> None:
        interactor, booking, classifier = self._interactor(None)
        await interactor.chat(MovaChatRequest(message="인턴 영화 시간표 보여줘"))
        # 레거시 경로: 예매 어휘 선분기 → booking.assist (분류기 생략)
        booking.assist.assert_awaited()
        booking.assist_slots.assert_not_awaited()

    async def test_evaluate_slots_pass_verified_title(self) -> None:
        slots = VerifiedSlots(
            intent="evaluate",
            title_text="옵세션",
            movie=_item(3, "옵세션"),
            region=None,
            time=None,
            chain=None,
            followup=False,
        )
        interactor, _, _ = self._interactor(slots)
        from mova.app.use_cases.market_chat_evaluation_interactor import EvaluationResult

        interactor._evaluation.evaluate.return_value = EvaluationResult(
            status="ok", reply="평가", card=None, evaluation=None
        )
        await interactor.chat(MovaChatRequest(message="옵세션 어때?"))
        self.assertEqual(interactor._evaluation.evaluate.await_args.kwargs["entities"], ["옵세션"])


if __name__ == "__main__":
    unittest.main()
