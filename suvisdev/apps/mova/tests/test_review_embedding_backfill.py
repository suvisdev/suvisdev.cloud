"""ReviewEmbeddingBackfillInteractor 단위 테스트.

세션 팩토리·embedder·ReviewsPgRepository를 전부 mock으로 대체해서 인터랙터의
분기 로직(body 없음 → skipped / embed 실패 → failed / 성공 → succeeded)만
격리 검증한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.use_cases.review_embedding_backfill_interactor import (  # noqa: E402
    ReviewEmbeddingBackfillInteractor,
)
from ontology.app.ports.output.hub_rag_errors import HubRagError  # noqa: E402


def _make_session_factory() -> MagicMock:
    """`async with factory() as session:` 을 흉내내는 팩토리 mock."""
    session = MagicMock()
    factory = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory


class ReviewEmbeddingBackfillInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_embed_one_skipped_when_body_missing(self) -> None:
        factory = _make_session_factory()
        embedder = AsyncMock()

        repo = MagicMock()
        repo.get_body_for_embedding = AsyncMock(return_value=None)
        repo.update_embedding = AsyncMock()

        interactor = ReviewEmbeddingBackfillInteractor(
            session_factory=factory, embedder=embedder
        )
        with patch(
            "mova.adapter.outbound.pg.market_reviews_pg_repository.ReviewsPgRepository",
            return_value=repo,
        ):
            outcome = await interactor.embed_one(42)

        self.assertEqual(outcome, "skipped")
        embedder.embed.assert_not_awaited()
        repo.update_embedding.assert_not_awaited()

    async def test_embed_one_saves_vector_on_success(self) -> None:
        factory = _make_session_factory()
        embedder = AsyncMock()
        embedder.embed = AsyncMock(return_value=[0.1] * 768)

        repo = MagicMock()
        repo.get_body_for_embedding = AsyncMock(return_value="정말 재밌었어요")
        repo.update_embedding = AsyncMock()

        interactor = ReviewEmbeddingBackfillInteractor(
            session_factory=factory, embedder=embedder
        )
        with patch(
            "mova.adapter.outbound.pg.market_reviews_pg_repository.ReviewsPgRepository",
            return_value=repo,
        ):
            outcome = await interactor.embed_one(7)

        self.assertEqual(outcome, "succeeded")
        embedder.embed.assert_awaited_once_with("정말 재밌었어요")
        repo.update_embedding.assert_awaited_once_with(7, [0.1] * 768)

    async def test_embed_one_returns_failed_on_embed_error(self) -> None:
        factory = _make_session_factory()
        embedder = AsyncMock()
        embedder.embed = AsyncMock(side_effect=HubRagError("429 quota", status_code=429))

        repo = MagicMock()
        repo.get_body_for_embedding = AsyncMock(return_value="본문")
        repo.update_embedding = AsyncMock()

        interactor = ReviewEmbeddingBackfillInteractor(
            session_factory=factory, embedder=embedder
        )
        with patch(
            "mova.adapter.outbound.pg.market_reviews_pg_repository.ReviewsPgRepository",
            return_value=repo,
        ):
            outcome = await interactor.embed_one(1)

        self.assertEqual(outcome, "failed")
        repo.update_embedding.assert_not_awaited()

    async def test_embed_missing_counts_all_outcomes(self) -> None:
        factory = _make_session_factory()
        embedder = AsyncMock()
        # 3건: 1 성공, 2 skip(body 없음), 3 실패
        embedder.embed = AsyncMock(
            side_effect=[
                [0.1] * 768,
                HubRagError("boom", status_code=500),
            ]
        )

        repo = MagicMock()
        # list_missing_embedding은 (id, body) 리스트 반환 — 3건 다 뽑힘
        repo.list_missing_embedding = AsyncMock(
            return_value=[(1, "본문 A"), (2, "본문 B"), (3, "본문 C")]
        )
        # 개별 처리 시 body 조회: 2번은 body가 사라졌다고 가정
        repo.get_body_for_embedding = AsyncMock(side_effect=["본문 A", None, "본문 C"])
        repo.update_embedding = AsyncMock()

        interactor = ReviewEmbeddingBackfillInteractor(
            session_factory=factory, embedder=embedder
        )
        with patch(
            "mova.adapter.outbound.pg.market_reviews_pg_repository.ReviewsPgRepository",
            return_value=repo,
        ):
            stats = await interactor.embed_missing(limit=None)

        self.assertEqual(stats, {"succeeded": 1, "skipped": 1, "failed": 1})
        # 성공한 건만 update_embedding 호출
        repo.update_embedding.assert_awaited_once_with(1, [0.1] * 768)


if __name__ == "__main__":
    unittest.main()
