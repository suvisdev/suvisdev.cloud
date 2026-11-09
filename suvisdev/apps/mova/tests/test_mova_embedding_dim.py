"""mova 임베딩 생성 경로가 mova 벡터 컬럼 차원(768)으로 만드는지 검증.

`GeminiEmbeddingAdapter` 기본 차원은 hub_knowledge 기준 EMBEDDING_DIM(1024)이라,
mova 경로가 기본 생성자를 쓰면 Gemini 호출은 성공하고 `reviews.embedding`·
`movies.embedding`(Vector(768)) 저장에서 실패한다(2026-10-20 리뷰 지적).
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

_ROOT = Path(__file__).resolve().parents[3]
_APPS = _ROOT / "apps"
for _p in (_ROOT, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from mova.adapter.outbound.orm.market_reviews_orm import MovaReview  # noqa: E402
from mova.adapter.outbound.orm.platform_user_taste_vectors_orm import (  # noqa: E402
    MovaUserTasteVector,
)
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie  # noqa: E402

_ADAPTER = "ontology.adapter.outbound.llm.gemini_embedding_adapter.GeminiEmbeddingAdapter"


def _column_dim(model: type, column: str) -> int:
    return int(model.__table__.c[column].type.dim)  # type: ignore[attr-defined]


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _session_factory() -> MagicMock:
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=MagicMock())
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx)


class MovaEmbeddingDimTests(unittest.IsolatedAsyncioTestCase):
    def test_mova_vector_columns_share_one_dim(self) -> None:
        dims = {
            _column_dim(MovaReview, "embedding"),
            _column_dim(MovaMovie, "embedding"),
            _column_dim(MovaUserTasteVector, "vector"),
        }
        self.assertEqual(dims, {768})

    def test_review_background_embedder_matches_reviews_column(self) -> None:
        from mova.dependencies.review_embedding_provider import (
            get_review_embedding_backfill_use_case,
        )

        with patch(
            "mova.dependencies.review_embedding_provider.get_mova_session_factory",
            return_value=MagicMock(),
        ):
            use_case = get_review_embedding_backfill_use_case()

        self.assertEqual(
            use_case._embedder._dimensions,  # type: ignore[attr-defined]
            _column_dim(MovaReview, "embedding"),
        )

    async def test_review_backfill_cli_embedder_matches_reviews_column(self) -> None:
        cli = _load_script("backfill_review_embeddings_cli")
        adapter_cls = MagicMock()
        interactor = MagicMock()
        interactor.return_value.embed_missing = AsyncMock(
            return_value={"succeeded": 0, "failed": 0, "skipped": 0}
        )
        with (
            patch.dict("os.environ", {"GEMINI_BACKFILL_API_KEY": ""}),
            patch("core.matrix.vauly_keymaker_secret_manager.get_keymaker"),
            patch(
                "core.matrix.grid_oracle_database_manager.get_mova_session_factory",
                return_value=_session_factory(),
            ),
            patch(_ADAPTER, adapter_cls),
            patch(
                "mova.app.use_cases.review_embedding_backfill_interactor."
                "ReviewEmbeddingBackfillInteractor",
                interactor,
            ),
        ):
            await cli._run(argparse.Namespace(limit=None, dry_run=False))

        self.assertEqual(
            adapter_cls.call_args.kwargs.get("dimensions"),
            _column_dim(MovaReview, "embedding"),
        )

    async def test_movie_backfill_cli_embedder_matches_movies_column(self) -> None:
        cli = _load_script("backfill_movie_embeddings_cli")
        adapter_cls = MagicMock()
        repo = MagicMock()
        repo.return_value.list_missing_embedding = AsyncMock(return_value=[])
        with (
            patch.dict("os.environ", {"GEMINI_BACKFILL_API_KEY": ""}),
            patch("core.matrix.vauly_keymaker_secret_manager.get_keymaker"),
            patch(
                "core.matrix.grid_oracle_database_manager.get_mova_session_factory",
                return_value=_session_factory(),
            ),
            patch(_ADAPTER, adapter_cls),
            patch("mova.adapter.outbound.pg.movies_pg_repository.MoviesPgRepository", repo),
        ):
            await cli._run(argparse.Namespace(limit=None, dry_run=False))

        self.assertEqual(
            adapter_cls.call_args.kwargs.get("dimensions"),
            _column_dim(MovaMovie, "embedding"),
        )


if __name__ == "__main__":
    unittest.main()
