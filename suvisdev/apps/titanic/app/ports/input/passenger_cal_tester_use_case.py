from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.adapter.inbound.api.schemas.passenger_cal_tester_schema import CalTesterSchema
from titanic.app.dtos.passenger_cal_tester_dto import CalTesterResponse, TestmodelResponse


class CalTesterUseCase(ABC):
    """cal_tester input port."""

    @abstractmethod
    async def test_model(self, test_set=None, train_result: dict | None = None) -> TestmodelResponse:
        """잭의 1등 모델로 test_set 예측 실행 후 최고 전략 선정."""
        pass

    @abstractmethod
    async def introduce_myself(self, schemas: CalTesterSchema)->CalTesterResponse:
        pass

    
