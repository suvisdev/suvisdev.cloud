"""PortfolioChatInteractor 정책 — 근거 없으면 LLM 미호출·고정 답, 잡음 컷, 프롬프트 구성, 히스토리 상한."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import ANY, AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto  # noqa: E402
from ontology.app.dtos.portfolio_chat_dto import (  # noqa: E402
    PortfolioChatCommand,
    PortfolioChatTurn,
)
from ontology.app.ports.output.hub_llm_port import HubLlmPort  # noqa: E402
from ontology.app.use_cases.portfolio_chat_interactor import (  # noqa: E402
    NO_CONTEXT_REPLY,
    SYSTEM_PROMPT,
    PortfolioChatInteractor,
)


class _FakeLlm(HubLlmPort):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        return "  답변  "


def _hit(title: str, content: str, score: float) -> HubKnowledgeHitDto:
    return HubKnowledgeHitDto(
        source_ref=f"portfolio:{title}#0", title=title, content=content, score=score
    )


def _interactor(
    hits: list[HubKnowledgeHitDto], llm: _FakeLlm
) -> tuple[PortfolioChatInteractor, AsyncMock]:
    repo = AsyncMock()
    repo.search.return_value = hits
    embedding = AsyncMock()
    embedding.embed.return_value = [0.1] * 1024
    return PortfolioChatInteractor(repository=repo, embedding=embedding, llm=llm), repo


class PortfolioChatInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_hits_returns_fixed_reply_without_llm(self) -> None:
        llm = _FakeLlm()
        interactor, _ = _interactor([], llm)
        dto = await interactor.chat(PortfolioChatCommand(message="오늘 날씨 어때?"))
        self.assertEqual(dto.reply, NO_CONTEXT_REPLY)
        self.assertEqual(dto.sources, ())
        self.assertEqual(llm.calls, [])

    async def test_noise_hits_are_filtered(self) -> None:
        llm = _FakeLlm()
        interactor, _ = _interactor([_hit("Mova", "영화", 0.05), _hit("Gildle", "산책", 0.04)], llm)
        dto = await interactor.chat(PortfolioChatCommand(message="아무거나"))
        self.assertEqual(dto.reply, NO_CONTEXT_REPLY)
        self.assertEqual(llm.calls, [])

    async def test_hits_build_grounded_prompt(self) -> None:
        llm = _FakeLlm()
        hits = [
            _hit("Mova", "AI 영화 추천 앱", 0.7),
            _hit("Mova", "LoRA 재학습", 0.6),
            _hit("Gildle", "산책", 0.5),
        ]
        interactor, _ = _interactor(hits, llm)
        history = (
            PortfolioChatTurn(role="user", content="안녕"),
            PortfolioChatTurn(role="assistant", content="반가워요"),
        )
        dto = await interactor.chat(
            PortfolioChatCommand(message="무슨 앱 만들었어?", history=history)
        )
        prompt, system = llm.calls[0]
        self.assertEqual(system, SYSTEM_PROMPT)
        self.assertIn("AI 영화 추천 앱", prompt)
        self.assertIn("사용자: 안녕", prompt)
        self.assertIn("AI: 반가워요", prompt)
        self.assertTrue(prompt.endswith("[질문]\n무슨 앱 만들었어?"))
        self.assertEqual(dto.reply, "답변")
        self.assertEqual(dto.sources, ("Mova", "Gildle"))

    async def test_history_is_trimmed_to_last_six_turns(self) -> None:
        llm = _FakeLlm()
        interactor, _ = _interactor([_hit("Mova", "영화", 0.7)], llm)
        history = tuple(PortfolioChatTurn(role="user", content=f"턴{i}") for i in range(8))
        await interactor.chat(PortfolioChatCommand(message="q", history=history))
        prompt, _ = llm.calls[0]
        self.assertNotIn("턴0", prompt)
        self.assertNotIn("턴1", prompt)
        self.assertIn("턴2", prompt)
        self.assertIn("턴7", prompt)

    async def test_out_of_scope_mark_is_replaced_with_fixed_reply(self) -> None:
        """모델이 [범위밖]을 내면 고정 거절 문구로 바꾸고 출처를 비운다(2026-09-28 사용자:
        "나에 관한 질문 말고는 대답하지 말아야"). 검색 점수로는 주제 안·밖이 갈리지 않았다."""
        from ontology.app.use_cases.portfolio_chat_interactor import OUT_OF_SCOPE_REPLY

        llm = _FakeLlm()
        llm.generate = AsyncMock(return_value=" [범위밖] ")  # type: ignore[method-assign]
        interactor, _ = _interactor([_hit("Mova", "AI 영화 추천 앱", 0.45)], llm)
        answer = await interactor.chat(PortfolioChatCommand(message="김치찌개 레시피 알려줘"))
        self.assertEqual(answer.reply, OUT_OF_SCOPE_REPLY)
        self.assertEqual(answer.sources, ())

    async def test_system_prompt_defines_scope_rule(self) -> None:
        llm = _FakeLlm()
        interactor, _ = _interactor([_hit("Mova", "AI 영화 추천 앱", 0.7)], llm)
        await interactor.chat(PortfolioChatCommand(message="mova가 뭐야"))
        self.assertIn("[범위밖]", llm.calls[0][1] or "")

    async def test_profile_chunks_always_included(self) -> None:
        """프로필 청크가 상위 6개 밖이어도 2개는 근거에 들어간다(ARDA 채용 문서가 '학력'을 선점)."""
        llm = _FakeLlm()
        pool = [_hit(f"ARDA {i}", "지원자 학력 필터", 0.6 - i * 0.01) for i in range(8)]
        pool += [
            HubKnowledgeHitDto(
                source_ref="portfolio:profile#2",
                title="프로필 — 학력",
                content="경상대학교",
                score=0.3,
            ),
            HubKnowledgeHitDto(
                source_ref="portfolio:profile#0", title="프로필 — 소개", content="풀스택", score=0.2
            ),
            HubKnowledgeHitDto(
                source_ref="portfolio:profile#4",
                title="프로필 — 기술",
                content="FastAPI",
                score=0.1,
            ),
        ]
        interactor, _ = _interactor(pool, llm)
        await interactor.chat(PortfolioChatCommand(message="학력이 어떻게 돼"))
        prompt = llm.calls[0][0]
        self.assertIn("경상대학교", prompt)
        self.assertIn("풀스택", prompt)
        self.assertNotIn("FastAPI", prompt)  # 프로필은 2개까지

    async def test_search_uses_portfolio_source(self) -> None:
        interactor, repo = _interactor([], _FakeLlm())
        await interactor.chat(PortfolioChatCommand(message="q"))
        repo.search.assert_awaited_once_with(ANY, k=30, source="portfolio_doc")


if __name__ == "__main__":
    unittest.main()
