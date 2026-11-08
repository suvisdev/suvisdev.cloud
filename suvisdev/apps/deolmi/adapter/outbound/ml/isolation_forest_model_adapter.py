"""2겹 탐지 — IsolationForest로 '정상에서 얼마나 벗어났나'를 본다.

모델 파일(DEOLMI_MODEL_PATH, scripts/retrain_model.py가 만든다)이 있으면 실데이터 모델을,
없으면 사람다운 가짜 표본으로 부트스트랩한다. 실사용 로그가 쌓이면 재학습으로 교체한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from deolmi.app.ports.output.anomaly_model_port import AnomalyModelPort

DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[3] / "runs" / "model.joblib"


def model_path() -> Path:
    return Path(os.getenv("DEOLMI_MODEL_PATH") or DEFAULT_MODEL_PATH)


@dataclass(frozen=True)
class ModelBundle:
    clf: IsolationForest
    dec_mean: float
    dec_std: float
    meta: dict[str, Any]


def bootstrap_samples(n: int = 2000, seed: int = 42) -> np.ndarray:
    """부트스트랩용 '사람다운' 표본 — 실데이터가 아니다.

    사람의 공통점: 간격이 들쭉날쭉하고, 마우스가 곡선이며, 생각하는 시간이 있다.
    열 순서는 scoring_policy.FEATURE_ORDER와 같아야 한다.
    """
    rng = np.random.default_rng(seed)
    return np.column_stack(
        [
            np.clip(rng.normal(120, 40, n), 5, None),  # move_count
            np.clip(rng.normal(2500, 800, n), 200, None),  # path_px
            rng.uniform(0.30, 0.80, n),  # straightness (사람은 꽤 굽음)
            np.clip(rng.normal(800, 300, n), 120, None),  # click_iv_mean
            np.clip(rng.normal(250, 100, n), 40, None),  # click_iv_std (변동 큼)
            np.clip(rng.normal(90, 40, n), 20, None),  # key_iv_std
            np.clip(rng.normal(6000, 2500, n), 900, None),  # dwell_ms
        ]
    )


def fit(samples: np.ndarray, meta: dict[str, Any]) -> ModelBundle:
    clf = IsolationForest(n_estimators=200, contamination=0.02, random_state=42)
    clf.fit(samples)
    dec = clf.decision_function(samples)
    return ModelBundle(clf, float(dec.mean()), float(dec.std()) or 1.0, meta)


class IsolationForestModelAdapter(AnomalyModelPort):
    def __init__(self, path: Path | None = None) -> None:
        path = path or model_path()
        if path.exists():
            self._bundle: ModelBundle = joblib.load(path)
            self._source = f"trained(n={self._bundle.meta.get('n', '?')})"
        else:
            self._bundle = fit(bootstrap_samples(), {"n": 0})
            self._source = "bootstrap"

    @property
    def source(self) -> str:
        return self._source

    def score(self, features: list[float]) -> float:
        dec = float(self._bundle.clf.decision_function(np.array([features]))[0])
        # 정상 평균보다 낮을수록(=더 바깥) 이상치. z로 환산 후 sigmoid.
        z = (self._bundle.dec_mean - dec) / self._bundle.dec_std
        return float(1.0 / (1.0 + np.exp(-z)))
