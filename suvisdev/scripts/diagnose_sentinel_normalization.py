"""06(Sentinel) H3 디버깅 2차 — val_split 버그 수정 + min-max 정규화 아티팩트 분리.

가설(사용자): anomalib PostProcessor의 image min-max 정규화가 validation
스코어 기준으로 [0,1] 클리핑을 하는데, 그 validation이 Folder 기본값
(val_split_mode=FROM_TEST, ratio=0.5)이 test셋 절반을 떼어가며 만들어진 것이라
왜곡됐을 수 있다. 클리핑으로 동점(특히 1.000)이 많이 생기면 AUROC가 그 자체로
깎인다.

이 스크립트는:
1. val_split_mode=NONE으로 바꿔 test 117개(good 42 + defect 75) 전부 평가
2. 정규화 켠 채(기본 post_processor)와 끈 채(enable_normalization=False) 각각
   fit+predict해서 AUROC를 나란히 비교
3. score==1.000 정확히 몇 개인지 normal/abnormal 각각 카운트(정규화 클리핑
   아티팩트인지 판정용)
4. raw(비정규화) score 기준 정상 이미지 상위 10장(가장 "이상해 보이는" 정상)
   파일명 출력

Usage (suvisdev 폴더에서):
  python scripts/diagnose_sentinel_normalization.py
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

from anomalib.data import Folder
from anomalib.data.utils.split import ValSplitMode
from anomalib.engine import Engine
from anomalib.models import Patchcore
from anomalib.post_processing import PostProcessor

_ROOT = "apps/ontology/resources/sentinel_poster"


def _make_datamodule() -> Folder:
    return Folder(
        name="sentinel_poster",
        root=_ROOT,
        normal_dir="train/good",
        test_split_mode="from_dir",
        normal_test_dir="test/good",
        abnormal_dir=["test/blur", "test/black_bar", "test/watermark"],
        # ValSplitMode.NONE은 val_dataloader 자체가 없어 Lightning fit이 크래시함
        # (PatchCore도 validation_step을 쓰기 때문). SAME_AS_TEST로 대체 —
        # val=test 전체(별도로 떼어가지 않음)라 test 117개가 그대로 평가된다.
        val_split_mode=ValSplitMode.SAME_AS_TEST,
        num_workers=0,
    )


def _run(*, enable_normalization: bool, results_dir: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    datamodule = _make_datamodule()
    post_processor = PostProcessor(enable_normalization=enable_normalization)
    model = Patchcore(post_processor=post_processor)
    engine = Engine(default_root_dir=results_dir)

    engine.fit(model=model, datamodule=datamodule)
    predictions = engine.predict(model=model, datamodule=datamodule, return_predictions=True)

    scores, labels, paths = [], [], []
    for batch in predictions:
        scores.extend(batch.pred_score.detach().cpu().numpy().tolist())
        labels.extend(batch.gt_label.detach().cpu().numpy().astype(int).tolist())
        paths.extend(batch.image_path)

    return np.array(scores), np.array(labels), paths


def main() -> None:
    print("=== [1] 정규화 ON (기본, val_split_mode=NONE으로 test 117개 전부) ===")
    scores_norm, labels_norm, paths_norm = _run(
        enable_normalization=True, results_dir="apps/ontology/runs/sentinel_anomaly_norm_on"
    )
    auroc_norm = roc_auc_score(labels_norm, scores_norm)
    print(f"샘플 수: {len(scores_norm)} (normal={sum(labels_norm==0)}, abnormal={sum(labels_norm==1)})")

    print("\n=== [2] 정규화 OFF (raw score, val_split_mode=NONE으로 test 117개 전부) ===")
    scores_raw, labels_raw, paths_raw = _run(
        enable_normalization=False, results_dir="apps/ontology/runs/sentinel_anomaly_norm_off"
    )
    auroc_raw = roc_auc_score(labels_raw, scores_raw)
    print(f"샘플 수: {len(scores_raw)} (normal={sum(labels_raw==0)}, abnormal={sum(labels_raw==1)})")

    print("\n=== 정규화 전/후 AUROC 비교 ===")
    print(f"정규화 ON  (min-max clamp): {auroc_norm:.4f}")
    print(f"정규화 OFF (raw score)    : {auroc_raw:.4f}")

    def _tie_counts(scores: np.ndarray, labels: np.ndarray) -> tuple[int, int]:
        is_one = np.isclose(scores, 1.0)
        normal_ties = int(np.sum(is_one & (labels == 0)))
        abnormal_ties = int(np.sum(is_one & (labels == 1)))
        return normal_ties, abnormal_ties

    n_norm, a_norm = _tie_counts(scores_norm, labels_norm)
    n_raw, a_raw = _tie_counts(scores_raw, labels_raw)
    print("\n=== score == 1.000 동점 개수 ===")
    print(f"정규화 ON : normal={n_norm}/{sum(labels_norm==0)}, abnormal={a_norm}/{sum(labels_norm==1)}")
    print(f"정규화 OFF: normal={n_raw}/{sum(labels_raw==0)}, abnormal={a_raw}/{sum(labels_raw==1)}")

    print("\n=== raw(비정규화) score 기준 정상 이미지 상위 10장 ===")
    normal_mask = labels_raw == 0
    normal_scores = scores_raw[normal_mask]
    normal_paths = [p for p, m in zip(paths_raw, normal_mask, strict=True) if m]
    order = np.argsort(-normal_scores)[:10]
    for i in order:
        print(f"{normal_paths[i].split('/')[-1]}: raw_score={normal_scores[i]:.4f}")


if __name__ == "__main__":
    main()
