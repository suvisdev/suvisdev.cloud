from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from titanic.adapter.inbound.api.schemas.crew_lowe_boat_schema import LoweBoatSchema
from titanic.app.dtos.crew_lowe_boat_dto import LoweBoatResponse


class LoweBoatUseCase(ABC):
    """crew_lowe_boat input port."""

    @abstractmethod
    def feature_engineering(self, train_set: pd.DataFrame) -> tuple[list[list[float]], list[int]]:
        """survived 포함 DataFrame → (X, y) 변환."""
        pass

    @abstractmethod
    async def introduce_myself(self, schemas: LoweBoatSchema) -> LoweBoatResponse:
        pass
