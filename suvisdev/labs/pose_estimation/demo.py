"""04(자세 추정) labs 데모 — 학습 없이 사전학습 YOLOv8-pose로 샘플 이미지 1장 추론.

최초 실행 시 yolov8n-pose.pt 가중치를 ultralytics가 실행 위치 기준으로 자동
다운로드한다(인터넷 필요, 이후엔 그 파일을 재사용 — 매 실행 재다운로드 아님).

실행: python -m labs.pose_estimation.demo [이미지 경로]
(이미지 경로 생략 시 samples/sample.jpg 사용 — ultralytics 기본 내장
zidane.jpg를 복사해 온 자세 추정 데모용 표준 샘플)
"""

from __future__ import annotations

import sys
from pathlib import Path

from labs.pose_estimation.adapters.yolov8_pose_adapter import YoloV8PoseAdapter

_DEFAULT_SAMPLE = Path(__file__).parent / "samples" / "sample.jpg"


def main(image_path: Path) -> None:
    adapter = YoloV8PoseAdapter()
    image_bytes = image_path.read_bytes()
    poses = adapter.estimate(image_bytes)

    if not poses:
        print(f"{image_path}: 검출된 사람 없음")
        return

    print(f"{image_path}: 사람 {len(poses)}명 검출")
    for i, pose in enumerate(poses):
        print(f"\n[사람 {i + 1}] box_confidence={pose.box_confidence:.3f}")
        for kp in pose.keypoints:
            print(f"  {kp.name:15s} x={kp.x:7.1f} y={kp.y:7.1f} conf={kp.confidence:.3f}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_SAMPLE
    main(path)
