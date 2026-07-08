from __future__ import annotations

import logging

from titanic.adapter.inbound.api.schemas.passenger_cal_tester_schema import CalTesterSchema
from titanic.app.dtos.passenger_cal_tester_dto import (
    CalTesterQuery,
    CalTesterResponse,
    KaggleScoreEntry,
    TestmodelResponse,
)
from titanic.app.ports.input.passenger_cal_tester_use_case import CalTesterUseCase
from titanic.app.ports.output.passenger_cal_tester_port import CalTesterPort

logger = logging.getLogger(__name__)


class CalTesterInteractor(CalTesterUseCase):
    def __init__(self, repository: CalTesterPort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: CalTesterSchema) -> CalTesterResponse:

        return await self._repository.introduce_myself(CalTesterQuery(
            id=schemas.id,
            name=schemas.name,
        ))
    
    async def test_model(self, test_set=None, train_result: dict | None = None) -> TestmodelResponse:
        """1등 모델로 test_set 예측 실행 후 최고 전략 선정"""
        result = train_result or {}
        accuracies: dict = result.get("accuracies", {})
        trained_strategies: dict = result.get("trained_strategies", {})
        X_test: list = result.get("X_test", [])
        train_samples: int = result.get("train_samples", 0)

        leaderboard = [
            KaggleScoreEntry(strategy=key, n_samples=train_samples, accuracy=acc)
            for key, acc in accuracies.items()
        ]
        leaderboard.sort(key=lambda entry: entry.accuracy, reverse=True)
        best_entry = leaderboard[0]

        # 1등 모델로 test_set 예측
        predictions: list[float] = []
        best_model = trained_strategies.get(best_entry.strategy)
        if best_model and X_test:
            predictions = best_model.predict_proba(X_test)
            logger.info(f"[CalTesterInteractor] {best_entry.strategy} 모델로 {len(predictions)}명 예측 완료")

        return TestmodelResponse(best=best_entry, leaderboard=leaderboard, predictions=predictions)
