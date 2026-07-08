from __future__ import annotations

import logging
from collections.abc import Mapping

from titanic.adapter.inbound.api.schemas.passenger_rose_model_schema import (
    RoseModelPredictSchema,
    RoseModelSchema,
    RoseModelTrainSchema,
)
from titanic.app.dtos.passenger_rose_model_dto import (
    RoseModelFeatureRow,
    RoseModelPredictResponse,
    RoseModelQuery,
    RoseModelResponse,
    RoseModelTrainResponse,
)
from titanic.app.ports.input.passenger_rose_model_use_case import RoseModelUseCase
from titanic.app.ports.output.passenger_rose_model_port import RoseModelPort
from titanic.app.ports.output.passenger_rose_model_strategy import RoseModelStrategy

logger = logging.getLogger(__name__)

_DEFAULT_AGE = 29.7  # 타이타닉 데이터셋 평균 나이 — 결측치 보완용 기본값
_DEFAULT_FARE = 32.2  # 타이타닉 데이터셋 평균 요금 — 결측치 보완용 기본값


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: str, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _encode_row(row: RoseModelFeatureRow, age_default: float, fare_default: float) -> list[float]:
    embarked = row.embarked.strip().upper()
    return [
        float(_to_int(row.pclass, 3)),
        1.0 if row.sex.strip().lower().startswith("m") else 0.0,
        _to_float(row.age, age_default),
        float(_to_int(row.sib_sp, 0)),
        float(_to_int(row.parch, 0)),
        _to_float(row.fare, fare_default),
        1.0 if embarked == "C" else 0.0,
        1.0 if embarked == "Q" else 0.0,
        1.0 if embarked == "S" else 0.0,
    ]


class RoseModelInteractor(RoseModelUseCase):
    def __init__(
        self,
        repository: RoseModelPort,
        strategies: Mapping[str, type[RoseModelStrategy]],
    ) -> None:
        self._repository = repository
        self._strategies = strategies

    async def introduce_myself(self, schemas: RoseModelSchema) -> RoseModelResponse:

        return await self._repository.introduce_myself(RoseModelQuery(
            id=schemas.id,
            name=schemas.name,
        ))

    async def train(self, schemas: RoseModelTrainSchema) -> RoseModelTrainResponse:
        rows = await self._repository.list_training_rows()
        X, y = self._build_dataset(rows)

        strategy = self._strategies[schemas.strategy]()
        # 모델을 영속화하지 않는 단순 데모 흐름 — 매 요청마다 전체 데이터로 재학습한다.
        strategy.fit(X, y)
        predicted = [1 if p >= 0.5 else 0 for p in strategy.predict_proba(X)]
        accuracy = (
            sum(1 for p, actual in zip(predicted, y, strict=False) if p == actual) / len(y)
            if y else 0.0
        )
        return RoseModelTrainResponse(strategy=schemas.strategy, n_samples=len(y), accuracy=accuracy)

    async def predict(self, schemas: RoseModelPredictSchema) -> RoseModelPredictResponse:
        rows = await self._repository.list_training_rows()
        X, y = self._build_dataset(rows)

        strategy = self._strategies[schemas.strategy]()
        strategy.fit(X, y)

        age_default, fare_default = self._impute_defaults(rows)
        target_row = RoseModelFeatureRow(
            pclass=schemas.pclass, sex=schemas.sex, age=schemas.age,
            sib_sp=schemas.sib_sp, parch=schemas.parch, fare=schemas.fare,
            embarked=schemas.embarked, survived="",
        )
        probability = strategy.predict_proba(
            [_encode_row(target_row, age_default, fare_default)],
        )[0]
        return RoseModelPredictResponse(
            strategy=schemas.strategy,
            survived=probability >= 0.5,
            probability=probability,
        )

    async def list_strategies(self) -> list[str]:
        return list(self._strategies.keys())

    def _build_dataset(self, rows: list[RoseModelFeatureRow]) -> tuple[list[list[float]], list[int]]:
        age_default, fare_default = self._impute_defaults(rows)
        X: list[list[float]] = []
        y: list[int] = []
        for row in rows:
            survived = row.survived.strip()
            if survived not in ("0", "1"):
                continue
            X.append(_encode_row(row, age_default, fare_default))
            y.append(int(survived))
        return X, y

    @staticmethod
    def _impute_defaults(rows: list[RoseModelFeatureRow]) -> tuple[float, float]:
        ages = [float(r.age) for r in rows if _is_number(r.age)]
        fares = [float(r.fare) for r in rows if _is_number(r.fare)]
        age_default = sum(ages) / len(ages) if ages else _DEFAULT_AGE
        fare_default = sum(fares) / len(fares) if fares else _DEFAULT_FARE
        return age_default, fare_default


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
