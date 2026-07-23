"""06(Sentinel) H3 디버깅 5차 — 범위 재정의(이상=포스터 아닌 이미지) 검증.

06_anomaly_detection_agent.md §5 재정의 이후 데이터셋:
- test/good            : 정상 포스터(기존 42장)
- test/non_poster_easy  : 진짜 이상(backdrop/cast profile, 40장)
- test/alt_poster_control: TMDB 대체 포스터(textless/비주력 언어판, 30장) —
  전부 공식 포스터라 **정상**이다. 이상으로 라벨링하면 모델이 "포스터 맞다"고
  옳게 판단해도 실패로 집계되므로, AUROC 라벨이 아니라 test/good과 점수
  분포를 비교하는 위양성 대조군으로만 쓴다.

anomalib Folder는 abnormal_dir에 넣은 폴더를 전부 label=1(abnormal)로
취급하므로, alt_poster_control도 일단 abnormal_dir에 넣어 점수는 뽑되
AUROC 계산에서는 제외하고 별도로 분포만 비교한다.

Usage (컨테이너 안 /suvisdev에서):
  python scripts/diagnose_sentinel_nonposter.py
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
_GROUPS = ["good", "non_poster_easy", "alt_poster_control"]


def _group_of(path: str) -> str:
    return path.split("/")[-2]


def _stats(name: str, arr: np.ndarray) -> str:
    return (
        f"{name:20s}: n={len(arr):3d} mean={arr.mean():7.3f} std={arr.std():6.3f} "
        f"p50={np.percentile(arr, 50):7.3f} p95={np.percentile(arr, 95):7.3f} "
        f"min={arr.min():7.3f} max={arr.max():7.3f}"
    )


def _manual_pairwise_auroc(pos: np.ndarray, neg: np.ndarray) -> float:
    """roc_auc_score와 별개로 P(pos > neg) + 0.5*P(pos == neg)를 직접 계산 —
    라벨 극성(양/음 어느 쪽이 1인지) 버그를 sklearn 호출과 무관하게 검증."""
    diff = pos[:, None] - neg[None, :]
    return float((np.sum(diff > 0) + 0.5 * np.sum(diff == 0)) / diff.size)


def _bootstrap_auroc_ci(
    pos: np.ndarray, neg: np.ndarray, *, n_boot: int = 2000, seed: int = 42
) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    aurocs = np.empty(n_boot)
    for i in range(n_boot):
        p = rng.choice(pos, size=len(pos), replace=True)
        n = rng.choice(neg, size=len(neg), replace=True)
        y = np.concatenate([np.zeros(len(n)), np.ones(len(p))])
        s = np.concatenate([n, p])
        aurocs[i] = roc_auc_score(y, s)
    return float(np.median(aurocs)), float(np.percentile(aurocs, 2.5)), float(np.percentile(aurocs, 97.5))


def main() -> None:
    datamodule = Folder(
        name="sentinel_poster",
        root=_ROOT,
        normal_dir="train/good",
        test_split_mode="from_dir",
        normal_test_dir="test/good",
        abnormal_dir=["test/non_poster_easy", "test/alt_poster_control"],
        val_split_mode=ValSplitMode.SAME_AS_TEST,
        num_workers=0,
    )
    model = Patchcore(post_processor=PostProcessor(enable_normalization=False))
    engine = Engine(default_root_dir="apps/ontology/runs/sentinel_anomaly_nonposter")
    engine.fit(model=model, datamodule=datamodule)
    predictions = engine.predict(model=model, datamodule=datamodule, return_predictions=True)

    scores, paths = [], []
    for batch in predictions:
        scores.extend(batch.pred_score.detach().cpu().numpy().tolist())
        paths.extend(batch.image_path)

    scores = np.array(scores)
    paths = np.array(paths)
    group_of = np.array([_group_of(p) for p in paths])

    by_group = {g: scores[group_of == g] for g in _GROUPS}

    print("=== 그룹별 점수 분포 ===")
    for g in _GROUPS:
        print(_stats(g, by_group[g]))

    print("\n=== easy 기준 AUROC(진짜 이상: good vs non_poster_easy) ===")
    good_scores = by_group["good"]
    easy_scores_all = by_group["non_poster_easy"]
    y = np.concatenate([np.zeros(len(good_scores)), np.ones(len(easy_scores_all))])
    s = np.concatenate([good_scores, easy_scores_all])
    auroc = roc_auc_score(y, s)
    manual_auroc = _manual_pairwise_auroc(easy_scores_all, good_scores)
    median_ci, lo_ci, hi_ci = _bootstrap_auroc_ci(easy_scores_all, good_scores)
    se_approx = np.sqrt(0.25 / min(len(good_scores), len(easy_scores_all)))  # 대략적 표준오차(0.5 기준)
    print(f"AUROC(sklearn) = {auroc:.4f}, 수동 pairwise 재계산 = {manual_auroc:.4f} (일치하면 라벨 극성 정상)")
    print(f"부트스트랩 95% CI = [{lo_ci:.4f}, {hi_ci:.4f}] (median={median_ci:.4f}, n_boot=2000)")
    print(f"n=({len(good_scores)},{len(easy_scores_all)})일 때 대략적 SE≈{se_approx:.4f} — 0.5와 통계적으로 구분되는지 참고")
    if lo_ci <= 0.5 <= hi_ci:
        verdict = "신호 없음(0.5가 CI 안에 있음 — 랜덤과 통계적으로 구분 안 됨)"
    elif auroc >= 0.9:
        verdict = "유효"
    else:
        verdict = "재검토 필요"
    print(f"판정: {verdict}")

    print("\n=== non_poster_easy 하위유형별 AUROC(backdrop vs cast profile) ===")
    easy_paths = paths[group_of == "non_poster_easy"]
    easy_scores = by_group["non_poster_easy"]
    for prefix in ("backdrop", "cast"):
        mask = np.array([p.split("/")[-1].startswith(prefix) for p in easy_paths])
        sub_scores = easy_scores[mask]
        y_sub = np.concatenate([np.zeros(len(by_group["good"])), np.ones(len(sub_scores))])
        s_sub = np.concatenate([by_group["good"], sub_scores])
        print(_stats(prefix, sub_scores) + f"  AUROC={roc_auc_score(y_sub, s_sub):.4f}")

    print("\n=== 위양성 대조: alt_poster_control(정상)이 good 대비 높게 오탐되는가 ===")
    good_p95 = np.percentile(by_group["good"], 95)
    exceed = by_group["alt_poster_control"] > good_p95
    print(f"good의 95th percentile 임계값: {good_p95:.3f}")
    print(
        f"alt_poster_control 중 그 임계값 초과: {exceed.sum()}/{len(exceed)} "
        f"({100 * exceed.mean():.1f}%) — 높으면 대체 포스터가 오탐될 위험"
    )


if __name__ == "__main__":
    main()
