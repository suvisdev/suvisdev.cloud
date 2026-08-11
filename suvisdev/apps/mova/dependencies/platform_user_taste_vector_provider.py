"""유저 취향 벡터 재계산 DI.

리뷰 임베딩 백필과 짝을 이루는 백그라운드 경로 인터랙터 — 요청 세션이 아닌
세션 팩토리를 직접 주입한다. Gemini 등 외부 의존이 없어(순수 SQL 가중 평균)
embedder를 받지 않는다.
"""

from __future__ import annotations

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from mova.app.use_cases.platform_user_taste_vector_interactor import (
    UserTasteVectorRecomputeInteractor,
)


def get_user_taste_vector_recompute_use_case() -> UserTasteVectorRecomputeInteractor:
    return UserTasteVectorRecomputeInteractor(
        session_factory=get_mova_session_factory(),
    )
