from __future__ import annotations

import numpy as np
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from titanic.app.ports.output.passenger_rose_model_strategy import RoseModelStrategy


class _SklearnStrategy(RoseModelStrategy):
    """fit/predict_proba를 갖춘 sklearn 호환 추정기를 감싸는 공통 베이스."""

    def __init__(self, estimator) -> None:
        self._estimator = estimator

    def fit(self, X: list[list[float]], y: list[int]) -> None:
        self._estimator.fit(np.asarray(X), np.asarray(y))

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        proba = self._estimator.predict_proba(np.asarray(X))
        return proba[:, 1].tolist()


class XGBoostStrategy(_SklearnStrategy):
    key = "xgboost"

    def __init__(self) -> None:
        super().__init__(XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            eval_metric="logloss", random_state=42,
        ))


class RandomForestStrategy(_SklearnStrategy):
    key = "random_forest"

    def __init__(self) -> None:
        super().__init__(RandomForestClassifier(n_estimators=200, random_state=42))


class LightGBMStrategy(_SklearnStrategy):
    key = "lightgbm"

    def __init__(self) -> None:
        super().__init__(LGBMClassifier(n_estimators=100, random_state=42, verbose=-1))


class CatBoostStrategy(_SklearnStrategy):
    key = "catboost"

    def __init__(self) -> None:
        super().__init__(CatBoostClassifier(iterations=200, verbose=False, random_state=42))


class LogisticRegressionStrategy(_SklearnStrategy):
    key = "logistic_regression"

    def __init__(self) -> None:
        super().__init__(LogisticRegression(max_iter=1000))


class DecisionTreeStrategy(_SklearnStrategy):
    key = "decision_tree"

    def __init__(self) -> None:
        super().__init__(DecisionTreeClassifier(max_depth=5, random_state=42))


class SVMStrategy(_SklearnStrategy):
    key = "svm"

    def __init__(self) -> None:
        super().__init__(SVC(probability=True, random_state=42))


class KNNStrategy(_SklearnStrategy):
    key = "knn"

    def __init__(self) -> None:
        super().__init__(KNeighborsClassifier(n_neighbors=5))


class NaiveBayesStrategy(_SklearnStrategy):
    key = "naive_bayes"

    def __init__(self) -> None:
        super().__init__(GaussianNB())


class KMeansPcaStrategy(RoseModelStrategy):
    """K-Means+PCA는 분류 모델이 아니므로, 군집의 다수 생존율을 예측값으로 매핑해 보조적으로 활용한다."""

    key = "kmeans_pca"

    def __init__(self) -> None:
        self._scaler = StandardScaler()
        self._pca = PCA(n_components=2, random_state=42)
        self._kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        self._cluster_survival_rate: dict[int, float] = {}

    def fit(self, X: list[list[float]], y: list[int]) -> None:
        X_arr = np.asarray(X)
        y_arr = np.asarray(y)
        reduced = self._pca.fit_transform(self._scaler.fit_transform(X_arr))
        clusters = self._kmeans.fit_predict(reduced)
        for cluster_id in set(clusters.tolist()):
            mask = clusters == cluster_id
            self._cluster_survival_rate[cluster_id] = (
                float(y_arr[mask].mean()) if mask.any() else 0.0
            )

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        reduced = self._pca.transform(self._scaler.transform(np.asarray(X)))
        clusters = self._kmeans.predict(reduced)
        return [self._cluster_survival_rate.get(int(c), 0.0) for c in clusters]


ROSE_MODEL_STRATEGIES: dict[str, type[RoseModelStrategy]] = {
    "xgboost": XGBoostStrategy,
    "random_forest": RandomForestStrategy,
    "lightgbm": LightGBMStrategy,
    "catboost": CatBoostStrategy,
    "logistic_regression": LogisticRegressionStrategy,
    "decision_tree": DecisionTreeStrategy,
    "svm": SVMStrategy,
    "knn": KNNStrategy,
    "naive_bayes": NaiveBayesStrategy,
    "kmeans_pca": KMeansPcaStrategy,
}


def build_all_strategies() -> dict[str, type[RoseModelStrategy]]:
    return ROSE_MODEL_STRATEGIES
