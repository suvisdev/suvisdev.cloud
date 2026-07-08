from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np
import pandas as pd

from titanic.adapter.inbound.api.schemas.passenger_jack_trainer_schema import JackTrainerSchema
from titanic.app.dtos.passenger_jack_trainer_dto import JackTrainerQuery, JackTrainerResponse
from titanic.app.ports.input.passenger_jack_trainer_use_case import JackTrainerUseCase
from titanic.app.ports.output.passenger_jack_trainer_port import JackTrainerPort

logger = logging.getLogger(__name__)


class JackTrainerInteractor(JackTrainerUseCase):

    def __init__(self, repository: JackTrainerPort, strategies: dict) -> None:
        self.repository = repository
        self._strategy_classes = strategies
        self._trained_strategies: dict = {}

    def _preprocess_features(self, df: pd.DataFrame) -> list[list[float]]:
        '''survived 컬럼 없는 DataFrame을 모델 입력 피처 리스트로 변환'''
        df["Title"] = df["name"].str.extract(r"([A-Za-z]+)\.", expand=False)
        df["Title"] = df["Title"].replace(
            ["Capt", "Col", "Don", "Dr", "Major", "Rev", "Jonkheer", "Dona", "Mme"], "Rare"
        )
        df["Title"] = df["Title"].replace(["Countess", "Lady", "Sir"], "Royal")
        df["Title"] = df["Title"].replace({"Mlle": "Mr", "Ms": "Miss"})
        title_mapping = {"Mr": 1, "Miss": 2, "Mrs": 3, "Master": 4, "Royal": 5, "Rare": 6}
        df["Title"] = df["Title"].map(title_mapping).fillna(0).astype(int)

        df["gender"] = df["gender"].map({"male": 0, "female": 1})

        bins = [-1, 0, 5, 12, 18, 24, 35, 60, np.inf]
        age_labels = ["Unknown", "Baby", "Child", "Teenager", "Student", "Young Adult", "Adult", "Senior"]
        age_title_mapping = {
            0: "Unknown", 1: "Baby", 2: "Child", 3: "Teenager",
            4: "Student", 5: "Young Adult", 6: "Adult", 7: "Senior",
        }
        age_mapping = {v: k for k, v in age_title_mapping.items()}
        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(-0.5)
        df["AgeGroup"] = pd.cut(df["age"], bins, labels=age_labels).astype(str)
        mask = df["AgeGroup"] == "Unknown"
        df.loc[mask, "AgeGroup"] = df.loc[mask, "Title"].map(age_title_mapping)
        df["AgeGroup"] = df["AgeGroup"].map(age_mapping).fillna(0).astype(int)

        df["embarked"] = df["embarked"].fillna("S").map({"S": 1, "C": 2, "Q": 3})

        df["fare"] = pd.to_numeric(df["fare"], errors="coerce").fillna(0.0)
        df["FareBand"] = (
            pd.qcut(df["fare"], 4, labels=[1, 2, 3, 4], duplicates="drop")
            .fillna(1).astype(int)
        )

        df["pclass"] = pd.to_numeric(df["pclass"], errors="coerce").fillna(3).astype(int)
        df["sib_sp"] = pd.to_numeric(df["sib_sp"], errors="coerce").fillna(0).astype(int)
        df["parch"] = pd.to_numeric(df["parch"], errors="coerce").fillna(0).astype(int)

        drop_cols = ["name", "age", "fare", "ticket", "cabin", "passenger_id"]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])

        return df.values.tolist()

    def _run_training(self, train_set: pd.DataFrame, test_set: pd.DataFrame | None = None) -> dict[str, Any]:
        logger.info("[JackTrainerInteractor] 학습 파이프라인 시작")

        train = train_set.copy()
        y_label = train["survived"].replace("", "0").astype(int).tolist()
        train = train.drop("survived", axis=1)
        X_train: list[list[float]] = self._preprocess_features(train)

        self._trained_strategies = {}
        trained_names = []
        accuracies: dict[str, float] = {}
        for key, StrategyClass in self._strategy_classes.items():
            strategy = StrategyClass()
            try:
                strategy.fit(X_train, y_label)
                proba = strategy.predict_proba(X_train)
                preds = [1 if p >= 0.5 else 0 for p in proba]
                acc = sum(p == y for p, y in zip(preds, y_label, strict=False)) / len(y_label)
                self._trained_strategies[key] = strategy
                accuracies[key] = acc
                trained_names.append(strategy.key)
                logger.info(f"[JackTrainerInteractor] {strategy.key} 학습 완료 | accuracy={acc:.3f}")
            except Exception as e:
                logger.warning(f"[JackTrainerInteractor] {key} 학습 실패 | error={e}")

        X_test: list[list[float]] = []
        test_meta: pd.DataFrame | None = None
        if test_set is not None and not test_set.empty:
            test = test_set.copy()
            test_meta = pd.DataFrame({
                "age":    pd.to_numeric(test["age"], errors="coerce"),
                "gender": test["gender"],
                "pclass": pd.to_numeric(test["pclass"], errors="coerce").fillna(3).astype(int),
            }).reset_index(drop=True)
            X_test = self._preprocess_features(test)
            logger.info(f"[JackTrainerInteractor] test_set 전처리 완료 | {len(X_test)}명")

        return {
            "train_samples": len(X_train),
            "trained_models": trained_names,
            "trained_strategies": self._trained_strategies,
            "accuracies": accuracies,
            "X_test": X_test,
            "test_meta": test_meta,
        }

    async def train_model(self, train_set: pd.DataFrame, test_set: pd.DataFrame | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(self._run_training, train_set, test_set)

    async def introduce_myself(self, schema: JackTrainerSchema) -> JackTrainerResponse:
        '''잭 트레이너의 자기소개 인터렉트'''
        return await self.repository.introduce_myself(JackTrainerQuery(
            id=schema.id,
            name=schema.name,
        ))
