from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from titanic.adapter.inbound.api.schemas.crew_hartley_violin_schema import HartleyViolinSchema
from titanic.app.dtos.crew_hartley_violin_dto import HartleyViolinResponse


class HartleyViolinUseCase(ABC):
    """crew_hartley_violin input port."""

    @abstractmethod
    def get_correlation_image(self, df: pd.DataFrame) -> bytes:
        """수치형 피처 간 상관관계 히트맵을 PNG 바이트로 반환한다."""
        pass

    @abstractmethod
    async def introduce_myself(self, schemas: HartleyViolinSchema) -> HartleyViolinResponse:
        pass
