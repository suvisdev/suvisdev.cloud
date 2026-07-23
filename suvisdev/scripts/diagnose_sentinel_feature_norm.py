"""06(Sentinel) H3 디버깅 4차 — additive/subtractive anomaly 가설 확증.

가설(사용자): PatchCore의 NN-distance는 "구조적 novelty"를 재는데, blur/black_bar/
watermark는 전부 정상 이미지 대비 정보량을 줄이는(subtractive) 손상이다. 정상
학습 분포(포스터)는 텍스트·인물·그래픽이 조밀해 patch feature의 L2 norm이 크고,
정보가 빠진 patch(블러·검은막)는 norm이 작아 원점 쪽으로 붕괴한다 — 그 결과
"정상 클러스터 전체"로부터 오히려 멀어져(균등하게 먼 지점이 되어) NN-distance가
커지는, 의미적 novelty가 아닌 구조적 부작용으로 anomaly score가 올라간다.

diagnose_sentinel_per_defect.py에서 이미 확인한 그룹별 평균 score
(normal=67.7, blur=70.7, black_bar=69.0, watermark=68.7)가 이 가설과 방향은
맞지만 "왜"를 직접 보여주지 않는다. 여기서는 메모리 뱅크에 들어가기 전 단계인
patch embedding 자체의 L2 norm을 그룹별로 뽑아 NN-distance와 나란히 비교한다.

Usage (컨테이너 안 /suvisdev에서):
  python scripts/diagnose_sentinel_feature_norm.py
"""

from __future__ import annotations

import numpy as np
import torch

from anomalib.data import Folder
from anomalib.data.utils.split import ValSplitMode
from anomalib.engine import Engine
from anomalib.models import Patchcore

_ROOT = "apps/ontology/resources/sentinel_poster"
_GROUPS = ["good", "blur", "black_bar", "watermark"]


def _group_of(path: str) -> str:
    return path.split("/")[-2]


def main() -> None:
    datamodule = Folder(
        name="sentinel_poster",
        root=_ROOT,
        normal_dir="train/good",
        test_split_mode="from_dir",
        normal_test_dir="test/good",
        abnormal_dir=["test/blur", "test/black_bar", "test/watermark"],
        val_split_mode=ValSplitMode.SAME_AS_TEST,
        num_workers=0,
    )
    model = Patchcore()
    engine = Engine(default_root_dir="apps/ontology/runs/sentinel_anomaly_feature_norm")
    engine.fit(model=model, datamodule=datamodule)

    net = model.model
    net.eval()
    device = next(net.parameters()).device

    datamodule.setup("test")
    loader = datamodule.test_dataloader()

    l2_norms: dict[str, list[float]] = {g: [] for g in _GROUPS}
    nn_dists: dict[str, list[float]] = {g: [] for g in _GROUPS}

    with torch.no_grad():
        for batch in loader:
            images = batch.image.to(device)
            paths = batch.image_path

            features = net.feature_extractor(images)
            features = {layer: net.feature_pooler(f) for layer, f in features.items()}
            embedding = net.generate_embedding(features)
            b, _c, h, w = embedding.shape
            patch_embedding = net.reshape_embedding(embedding)  # (b*h*w, dim)

            patch_scores, _locations = net.nearest_neighbors(embedding=patch_embedding, n_neighbors=1)
            patch_scores = patch_scores.reshape(b, h * w)
            patch_norms = patch_embedding.norm(dim=1).reshape(b, h * w)

            for i, path in enumerate(paths):
                g = _group_of(path)
                if g not in l2_norms:
                    continue
                l2_norms[g].append(patch_norms[i].mean().item())
                nn_dists[g].append(patch_scores[i].mean().item())

    print("=== 그룹별 patch feature L2 norm(이미지당 평균, 정보량 proxy) ===")
    for g in _GROUPS:
        arr = np.array(l2_norms[g])
        print(f"{g:10s}: n={len(arr):3d} mean={arr.mean():.3f} std={arr.std():.3f} min={arr.min():.3f} max={arr.max():.3f}")

    print("\n=== 그룹별 NN distance(top-1 patch score, 이미지당 평균) ===")
    for g in _GROUPS:
        arr = np.array(nn_dists[g])
        print(f"{g:10s}: n={len(arr):3d} mean={arr.mean():.3f} std={arr.std():.3f} min={arr.min():.3f} max={arr.max():.3f}")

    print("\n=== L2 norm vs NN distance 상관관계(전 샘플 pooled) ===")
    all_norms = np.concatenate([l2_norms[g] for g in _GROUPS])
    all_dists = np.concatenate([nn_dists[g] for g in _GROUPS])
    corr = np.corrcoef(all_norms, all_dists)[0, 1]
    print(f"pearson r(L2 norm, NN distance) = {corr:.4f}  (음수면 '정보량 적을수록 거리 큼' 가설 지지)")

    print("\n=== 그룹별 L2 norm vs NN distance 상관관계(그룹 내부) ===")
    for g in _GROUPS:
        r = np.corrcoef(l2_norms[g], nn_dists[g])[0, 1]
        print(f"{g:10s}: r={r:.4f}")


if __name__ == "__main__":
    main()
