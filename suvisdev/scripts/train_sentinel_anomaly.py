"""06(Sentinel) H3 Phase B — 포스터 도메인 PatchCore memory bank 구축 + AUROC 측정.

Phase A(verify_patchcore_mvtec_sanity.py)에서 파이프라인 정합성은 이미 검증됐다.
여기서는 apps/ontology/resources/sentinel_poster(정상 포스터 + 합성 손상)로
실제 memory bank를 구축하고 image AUROC를 측정한다.

가중치는 apps/ontology/runs/sentinel_anomaly/에 저장(기존 YOLO/genre_classify
관례대로 .gitignore 대상).

Usage (suvisdev 폴더에서):
  python scripts/train_sentinel_anomaly.py
"""

from __future__ import annotations

from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.models import Patchcore

_ROOT = "apps/ontology/resources/sentinel_poster"
_RESULTS_DIR = "apps/ontology/runs/sentinel_anomaly"


def main() -> None:
    datamodule = Folder(
        name="sentinel_poster",
        root=_ROOT,
        normal_dir="train/good",
        test_split_mode="from_dir",
        normal_test_dir="test/good",
        abnormal_dir=["test/blur", "test/black_bar", "test/watermark"],
        num_workers=0,  # 컨테이너 /dev/shm 64MB 제약 — Phase A와 동일 우회
    )
    model = Patchcore()
    engine = Engine(default_root_dir=_RESULTS_DIR)

    engine.fit(model=model, datamodule=datamodule)
    results = engine.test(model=model, datamodule=datamodule)

    print("RESULTS:", results)


if __name__ == "__main__":
    main()
