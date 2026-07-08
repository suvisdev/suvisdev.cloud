from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from titanic.adapter.inbound.api.schemas.passenger_jack_trainer_schema import JackTrainerSchema
from titanic.app.dtos.passenger_jack_trainer_dto import JackTrainerResponse


class JackTrainerUseCase(ABC):

    @abstractmethod
    async def train_model(
        self,
        X_train: list[list[float]],
        y_label: list[int],
        X_test: list[list[float]],
        test_meta: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """피처 엔지니어링이 완료된 데이터를 받아 모델을 훈련하고 결과를 반환한다."""
        pass

    @abstractmethod
    async def introduce_myself(self, schema: JackTrainerSchema) -> JackTrainerResponse:
        pass
