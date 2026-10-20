"""쌓인 로그로 이상 탐지 모델을 재학습한다 — 가짜 표본을 실데이터로 교체하는 고리.

allow로 판정된 세션 중 완전한 것만 모아 IsolationForest를 다시 학습하고
DEOLMI_MODEL_PATH(기본 apps/deolmi/runs/model.joblib)에 저장한다. 다음 기동부터 쓰인다.
데이터가 적으면(200건 미만) 생략하고 부트스트랩을 유지한다.

    cd suvisdev && PYTHONPATH="$PWD:$PWD/apps" python -m deolmi.scripts.retrain_model
"""

from __future__ import annotations

import asyncio
import time

import joblib
import numpy as np

from core.matrix.grid_oracle_database_manager import get_db
from deolmi.adapter.outbound.ml.isolation_forest_model_adapter import fit, model_path
from deolmi.adapter.outbound.repositories.event_pg_repository import EventPgRepository
from deolmi.domain.services.scoring_policy import to_features

MIN_SAMPLES = 200


def _complete(s: dict[str, float]) -> bool:
    # 사람다운 완전한 세션만: 마우스 움직임·체류 시간·키 리듬이 실제로 있는 것.
    return s.get("move_count", 0) > 0 and s.get("dwell_ms", 0) > 0 and s.get("key_iv_std", 0) > 0


async def main() -> None:
    async for session in get_db():
        rows = await EventPgRepository(session).signals_by_verdict("allow", limit=100_000)
    vecs = [to_features(s) for s in rows if _complete(s)]
    print(f"allow 로그 {len(rows)}건 중 학습 가능한 완전 세션 {len(vecs)}건")
    if len(vecs) < MIN_SAMPLES:
        print(f"데이터 부족(<{MIN_SAMPLES}건) — 재학습 생략, 부트스트랩 유지")
        return
    path = model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(fit(np.array(vecs), {"n": len(vecs), "trained_at": time.time()}), path)
    print(f"재학습 완료 → {path} (표본 {len(vecs)}건)")


if __name__ == "__main__":
    asyncio.run(main())
