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

    # 간격 통계는 횟수가 적으면 0이다(SDK: 간격 1개면 표준편차 0, 클릭 1번이면 평균도 0). 입력칸 하나·버튼 하나인
    # 폼의 사람은 대부분 클릭 1~2번이고, 좌석만 고르는 예매처럼 타이핑이 없을 수도 있다. 이 세션을 표본에 넣지 않으면
    # 모델이 0을 '이상'으로 본다(11-08 실측: 클릭 2번인 사람 세션 0.92 → 차단). 기계적 간격은 규칙이 횟수를 보고 잡는다.
    # 횟수·거리·시간은 사람마다 몇 배씩 차이 나는 긴 꼬리 분포라 로그정규로 뽑는다(정규분포로 좁게 잡으면
    # 마우스를 많이 움직이거나 천천히 입력한 사람을 이상치로 본다). 클릭 2번이면 간격이 타이핑 시간을 통째로 담는다.
    def lognormal(median: float, sigma: float, low: float) -> np.ndarray:
        return np.clip(rng.lognormal(np.log(median), sigma, n), low, None)

    clicks = rng.choice([1, 2, 3], size=n, p=[0.3, 0.3, 0.4])  # 3 = 세 번 이상
    click_iv_mean = np.where(
        clicks == 1,
        0.0,
        np.where(
            clicks == 2,
            lognormal(3000, 0.6, 150),
            lognormal(800, 0.5, 120),
        ),
    )
    # 클릭 사이에는 타이핑·입력칸 이동이 끼어 간격 편차가 크다(11-09 공격 시험: 두 칸 채우면
    # 500~1000). 예전 정규(250, 100)는 이를 이상치로 봤다. 키 간격은 SDK가 1초 넘는 멈춤을 뺀다.
    click_iv_std = np.where(clicks == 3, lognormal(450, 0.8, 40), 0.0)
    typed = rng.random(n) < 0.75
    key_iv_std = np.where(typed, np.clip(rng.normal(90, 40, n), 20, None), 0.0)
    return np.column_stack(
        [
            lognormal(120, 0.6, 5),  # move_count
            lognormal(2200, 0.6, 200),  # path_px
            rng.uniform(0.30, 0.80, n),  # straightness (사람은 꽤 굽음)
            click_iv_mean,
            click_iv_std,
            key_iv_std,
            lognormal(6000, 0.6, 900),  # dwell_ms
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
