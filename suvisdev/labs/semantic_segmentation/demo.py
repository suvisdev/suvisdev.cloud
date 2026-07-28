"""03(Loom) labs 데모 — 학습 없이 사전학습 LR-ASPP로 샘플 이미지 1장 분할.

최초 실행 시 lraspp_mobilenet_v3_large 가중치를 torch hub가 자동
다운로드한다(인터넷 필요, 이후엔 ~/.cache/torch/hub/checkpoints/ 재사용).

이 모델은 Pascal VOC 21개 클래스로 학습돼 도로/보도 클래스가 없다 — 이
데모는 "서울 보도 검출"(03이 막힌 실제 용도)과 무관한 일반 사물 분할
기법 확인용이다(labs/README.md §03 참고).

실행: python -m labs.semantic_segmentation.demo [이미지 경로]
"""

from __future__ import annotations

import sys
from pathlib import Path

from labs.semantic_segmentation.adapters.lraspp_adapter import LrasppSegmentationAdapter

_DEFAULT_SAMPLE = Path(__file__).parent / "samples" / "sample.jpg"


def main(image_path: Path) -> None:
    adapter = LrasppSegmentationAdapter()
    image_bytes = image_path.read_bytes()
    result = adapter.segment(image_bytes)

    print(f"{image_path}: {result.width}x{result.height} 마스크, 클래스 {len(result.detected_classes)}개 검출")
    total_pixels = result.width * result.height
    for detected in sorted(result.detected_classes, key=lambda d: d.pixel_count, reverse=True):
        ratio = detected.pixel_count / total_pixels
        print(
            f"  {detected.label:15s} pixel={detected.pixel_count:6d} "
            f"({ratio:5.1%})  avg_confidence={detected.confidence:.3f}"
        )


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_SAMPLE
    main(path)
