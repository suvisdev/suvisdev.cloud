"""06(Sentinel) H3 디버깅 — engine.test()의 0.525가 계측 버그인지 실제 성능인지 판정.

engine.predict()로 샘플별 pred_score/gt_label을 직접 뽑아 sklearn으로 수동
AUROC를 계산해 engine.test() 결과와 대조한다. 대조군으로 Phase A(MVTec bottle,
image_AUROC=1.0)도 같이 표기.

Usage (suvisdev 폴더에서):
  python scripts/diagnose_sentinel_anomaly.py
"""

from __future__ import annotations

import numpy as np
from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.models import Patchcore
from sklearn.metrics import roc_auc_score

_ROOT = "apps/ontology/resources/sentinel_poster"
_RESULTS_DIR = "apps/ontology/runs/sentinel_anomaly"
_PHASE_A_AUROC = 1.0  # verify_patchcore_mvtec_sanity.py 실측(2026-07-23), MVTec bottle


def main() -> None:
    datamodule = Folder(
        name="sentinel_poster",
        root=_ROOT,
        normal_dir="train/good",
        test_split_mode="from_dir",
        normal_test_dir="test/good",
        abnormal_dir=["test/blur", "test/black_bar", "test/watermark"],
        num_workers=0,
    )
    model = Patchcore()
    engine = Engine(default_root_dir=_RESULTS_DIR)

    engine.fit(model=model, datamodule=datamodule)

    memory_bank = model.model.memory_bank
    print(f"\n=== memory bank(coreset) 크기: {tuple(memory_bank.shape)} ===\n")

    predictions = engine.predict(model=model, datamodule=datamodule, return_predictions=True)

    scores: list[float] = []
    labels: list[int] = []
    paths: list[str] = []
    for batch in predictions:
        scores.extend(batch.pred_score.detach().cpu().numpy().tolist())
        labels.extend(batch.gt_label.detach().cpu().numpy().astype(int).tolist())
        paths.extend(batch.image_path)

    scores_arr = np.array(scores)
    labels_arr = np.array(labels)

    manual_auroc = roc_auc_score(labels_arr, scores_arr)

    normal_scores = scores_arr[labels_arr == 0]
    abnormal_scores = scores_arr[labels_arr == 1]

    print(f"=== 수동 계산 AUROC(sklearn): {manual_auroc:.4f} ===")
    print(f"=== Phase A(MVTec bottle) AUROC 대조군: {_PHASE_A_AUROC:.4f} ===\n")

    print(
        f"전체 샘플 수: {len(scores_arr)} (normal={len(normal_scores)}, abnormal={len(abnormal_scores)})"
    )
    print(
        f"normal score  min/max/mean/std: "
        f"{normal_scores.min():.4f} / {normal_scores.max():.4f} / "
        f"{normal_scores.mean():.4f} / {normal_scores.std():.4f}"
    )
    print(
        f"abnormal score min/max/mean/std: "
        f"{abnormal_scores.min():.4f} / {abnormal_scores.max():.4f} / "
        f"{abnormal_scores.mean():.4f} / {abnormal_scores.std():.4f}"
    )

    print("\n=== score/label 샘플 10개 ===")
    for i in range(min(10, len(scores_arr))):
        print(
            f"{paths[i].split('/')[-2]}/{paths[i].split('/')[-1]}: score={scores_arr[i]:.4f} label={labels_arr[i]}"
        )


if __name__ == "__main__":
    main()
