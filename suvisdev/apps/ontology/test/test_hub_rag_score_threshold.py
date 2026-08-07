"""HubRagInteractor.search_movies 유사도 하한 — 임베딩 공간 불일치 방어.

2026-08-07 사고 재발 방지: 저장된 벡터(nomic)와 다른 백엔드(Gemini)로 쿼리를
임베딩하면 차원이 같아 에러 없이 유사도 ~0.04짜리 무작위 이웃이 반환되고,
그게 "정상 히트"로 취급돼 태그 검색 경로를 대체해버렸다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto  # noqa: E402
from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor  # noqa: E402


def _hit(title: str, score: float) -> HubKnowledgeHitDto:
    return HubKnowledgeHitDto(source_ref="1", title=title, content="", score=score)


def _interactor(hits: list[HubKnowledgeHitDto]) -> HubRagInteractor:
    repo = AsyncMock()
    repo.search.return_value = hits
    embedding = AsyncMock()
    embedding.embed.return_value = [0.1] * 768
    return HubRagInteractor(repository=repo, embedding=embedding)


class SearchScoreThresholdTests(unittest.IsolatedAsyncioTestCase):
    async def test_noise_level_hits_are_discarded(self) -> None:
        """임베딩 공간이 다르면 이런 점수가 나온다 — 태그 폴백으로 넘어가야 한다."""
        interactor = _interactor([_hit("증오", 0.046), _hit("아이스 에이지 2", 0.040)])

        result = await interactor.search_movies("액션 영화")

        self.assertEqual(result, [])

    async def test_meaningful_hits_pass(self) -> None:
        interactor = _interactor([_hit("다크 나이트", 0.72), _hit("인셉션", 0.61)])

        result = await interactor.search_movies("액션 영화")

        self.assertEqual([h.title for h in result], ["다크 나이트", "인셉션"])

    async def test_mixed_keeps_only_above_threshold(self) -> None:
        interactor = _interactor([_hit("다크 나이트", 0.72), _hit("잡음", 0.03)])

        result = await interactor.search_movies("액션 영화")

        self.assertEqual([h.title for h in result], ["다크 나이트"])


if __name__ == "__main__":
    unittest.main()
