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
        train_set: pd.DataFrame,
        test_set: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """원본 DataFrame을 받아 전처리·학습을 수행하고 결과를 반환한다."""
        pass

    @abstractmethod
    async def introduce_myself(self, schema: JackTrainerSchema) -> JackTrainerResponse:
        pass
