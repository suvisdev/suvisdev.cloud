"""유저 취향 벡터 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.platform_user_taste_vector_dto import UserTasteVectorDto


class UserTasteVectorRepositoryPort(ABC):
    @abstractmethod
    async def upsert(self, user_id: int, vector: list[float] | None, review_count: int) -> None:
        """유저 취향 벡터 저장/갱신. UNIQUE(user_id) 기준 upsert."""

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> UserTasteVectorDto | None:
        """유저 취향 벡터 조회."""

    @abstractmethod
    async def list_user_ids_with_rated_reviews(self, limit: int | None) -> list[int]:
        """embedding·rating이 모두 있는 리뷰를 가진 유저 id 목록 — CLI 백필용.

        user_taste_vectors 존재/최신성은 판정하지 않는다(idempotent 재계산이
        저렴하고, 판정 로직 자체가 stale 위험이라 여기서는 후보만 뽑는다).
        """
