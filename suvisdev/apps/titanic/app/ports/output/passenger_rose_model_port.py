from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.app.dtos.passenger_rose_model_dto import (
    RoseModelFeatureRow,
    RoseModelQuery,
    RoseModelResponse,
)


class RoseModelPort(ABC):
    """passenger_rose_model output port."""

    @abstractmethod
    def introduce_myself(self, query: RoseModelQuery)->RoseModelResponse:
        pass

    @abstractmethod
    async def list_training_rows(self) -> list[RoseModelFeatureRow]:
        """James가 적재한 titanic_passengers·titanic_bookings 조인 결과를 반환."""
        pass
