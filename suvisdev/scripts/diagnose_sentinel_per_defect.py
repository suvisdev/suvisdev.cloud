"""06(Sentinel) H3 디버깅 3차 — 손상 유형별 AUROC 분해.

정규화 OFF(raw score), val_split_mode=SAME_AS_TEST(test 117개 전부 평가)
조건에서, normal(42) vs 각 defect 유형(blur/black_bar/watermark, 25장씩)을
개별적으로 짝지어 AUROC를 따로 계산한다. 합친 0.528이 유형별 편차를
가리고 있을 수 있어서(black_bar는 개별 점수가 0.70~1.0로 높게 나온 바 있음).

Usage (suvisdev 폴더에서):
  python scripts/diagnose_sentinel_per_defect.py
"""

from __future__ import annotations

import numpy as np
from anomalib.data import Folder
from anomalib.data.utils.split import ValSplitMode
from anomalib.engine import Engine
from anomalib.models import Patchcore
from anomalib.post_processing import PostProcessor
from sklearn.metrics import roc_auc_score

_ROOT = "apps/ontology/resources/sentinel_poster"
_DEFECT_TYPES = ["blur", "black_bar", "watermark"]


def main() -> None:
    datamodule = Folder(
        name="sentinel_poster",
        root=_ROOT,
        normal_dir="train/good",
        test_split_mode="from_dir",
        normal_test_dir="test/good",
        abnormal_dir=[f"test/{d}" for d in _DEFECT_TYPES],
        val_split_mode=ValSplitMode.SAME_AS_TEST,
        num_workers=0,
    )
    model = Patchcore(post_processor=PostProcessor(enable_normalization=False))
    engine = Engine(default_root_dir="apps/ontology/runs/sentinel_anomaly_per_defect")

    engine.fit(model=model, datamodule=datamodule)
    predictions = engine.predict(model=model, datamodule=datamodule, return_predictions=True)

    scores, labels, paths = [], [], []
    for batch in predictions:
        scores.extend(batch.pred_score.detach().cpu().numpy().tolist())
        labels.extend(batch.gt_label.detach().cpu().numpy().astype(int).tolist())
        paths.extend(batch.image_path)

    scores = np.array(scores)
    labels = np.array(labels)
    paths = np.array(paths)

    def _defect_of(path: str) -> str:
        return path.split("/")[-2]

    defect_names = np.array([_defect_of(p) for p in paths])

    normal_scores = scores[defect_names == "good"]
    print(
        f"normal(test/good) n={len(normal_scores)}, mean={normal_scores.mean():.3f}, std={normal_scores.std():.3f}"
    )

    print("\n=== 손상 유형별 AUROC (normal 42 vs 해당 유형) ===")
    for defect in _DEFECT_TYPES:
        defect_scores = scores[defect_names == defect]
        y = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(defect_scores))])
        s = np.concatenate([normal_scores, defect_scores])
        auroc = roc_auc_score(y, s)
        print(
            f"{defect:10s}: AUROC={auroc:.4f}  "
            f"n={len(defect_scores)}  mean={defect_scores.mean():.3f}  std={defect_scores.std():.3f}"
        )


if __name__ == "__main__":
    main()
