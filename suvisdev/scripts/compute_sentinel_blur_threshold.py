"""06(Sentinel) §6.5 방향 결정 — 화질 저하(blur) 분리 구현.

PatchCore는 blur를 어느 정도 잡지만(§5.2, AUROC 0.573) 그 이상은 아니고
Sentinel의 원래 목적(포스터가 아닌 이미지 판별)과도 안 맞다고 판단해
Laplacian variance라는 무참조(no-reference) 화질 지표로 분리했다(§6.5).

임계값은 정상 포스터 232장(genre_classifier_train 전체, train+val)의
Laplacian variance **하위 5퍼센타일**로 산출한다. Laplacian variance는
이미지 해상도에 따라 절대값이 달라지므로(해상도가 크면 고주파 성분이 더
많이 잡혀 값이 커짐) 계산 전 고정 크기로 **해상도 정규화**한다 — PatchCore
전처리와 동일한 256x256을 사용해 두 파이프라인의 "동일 조건" 기준을 맞췄다.

검증용으로 test/blur(합성 블러 25장, Phase B 잔존 리소스)에 대해서도 같은
지표를 계산해 임계값 아래로 얼마나 떨어지는지 대조한다 — 별도 학습 없는
경량 지표라 PatchCore와 달리 blur만큼은 뚜렷이 갈릴 것으로 예상.

Usage (컨테이너 또는 호스트, PIL+opencv만 필요 — suvisdev 폴더에서):
  python scripts/compute_sentinel_blur_threshold.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_NORMAL_ROOT = Path("apps/ontology/resources/genre_classifier_train")
_BLUR_TEST_DIR = Path("apps/ontology/resources/sentinel_poster/test/blur")
_RESIZE = (256, 256)  # PatchCore 전처리와 동일 — 해상도 정규화
_PERCENTILE = 5


def _laplacian_variance(path: Path) -> float:
    img = Image.open(path).convert("L").resize(_RESIZE, Image.BILINEAR)
    arr = np.array(img)
    return float(cv2.Laplacian(arr, cv2.CV_64F).var())


def main() -> None:
    normal_paths = sorted(_NORMAL_ROOT.glob("*/*/*.jpg"))
    assert len(normal_paths) == 232, f"예상 232장, 실제 {len(normal_paths)}장"

    normal_scores = np.array([_laplacian_variance(p) for p in normal_paths])
    threshold = float(np.percentile(normal_scores, _PERCENTILE))

    print(f"=== 정상 포스터 {len(normal_scores)}장 Laplacian variance 분포(256x256 정규화 후) ===")
    print(
        f"mean={normal_scores.mean():.1f} std={normal_scores.std():.1f} "
        f"p5={np.percentile(normal_scores, 5):.1f} p50={np.percentile(normal_scores, 50):.1f} "
        f"p95={np.percentile(normal_scores, 95):.1f} min={normal_scores.min():.1f} max={normal_scores.max():.1f}"
    )
    print(f"\n블러 임계값(하위 {_PERCENTILE}퍼센타일) = {threshold:.2f}")
    print("→ Laplacian variance가 이 값보다 낮으면 blur로 판정")

    if _BLUR_TEST_DIR.exists():
        blur_paths = sorted(_BLUR_TEST_DIR.glob("*.jpg"))
        blur_scores = np.array([_laplacian_variance(p) for p in blur_paths])
        below = blur_scores < threshold
        print(f"\n=== 대조: 합성 블러(test/blur, n={len(blur_scores)}) ===")
        print(f"mean={blur_scores.mean():.1f} std={blur_scores.std():.1f}")
        print(f"임계값 미만(정상 판정 실패=blur로 잡힘) 비율: {below.sum()}/{len(below)} ({100 * below.mean():.1f}%)")


if __name__ == "__main__":
    main()
