from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.adapter.inbound.api.schemas.passenger_rose_model_schema import (
    RoseModelPredictSchema,
    RoseModelSchema,
    RoseModelTrainSchema,
)
from titanic.app.dtos.passenger_rose_model_dto import (
    RoseModelPredictResponse,
    RoseModelResponse,
    RoseModelTrainResponse,
)


class RoseModelUseCase(ABC):
    """rose_model input port."""

    @abstractmethod
    async def introduce_myself(self, schemas: RoseModelSchema)->RoseModelResponse:
        pass

    @abstractmethod
    async def train(self, schemas: RoseModelTrainSchema) -> RoseModelTrainResponse:
        """titanic-algorithm.md TOP 10 전략 중 하나를 DB 적재 데이터로 학습·평가."""
        pass

    @abstractmethod
    async def predict(self, schemas: RoseModelPredictSchema) -> RoseModelPredictResponse:
        """전략을 학습시킨 뒤 입력된 승객 1명의 생존 여부를 예측."""
        pass

    @abstractmethod
    async def list_strategies(self) -> list[str]:
        """제공 가능한 전략 키 목록 (titanic-algorithm.md TOP 10)."""
        pass
