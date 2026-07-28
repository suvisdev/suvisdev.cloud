"""YOLOv8-pose(ultralytics) 어댑터 — PoseEstimationPort 구현체.

사전학습 가중치(yolov8n-pose.pt)는 최초 실행 시 ultralytics가 실행 위치
기준으로 자동 다운로드한다(인터넷 필요, 이후엔 그 파일을 재사용). 학습은
하지 않고 사전학습 모델 추론만 한다 — GPU 없는 환경(CPU-only)을 전제로
가장 가벼운 n(nano) 크기를 쓴다.
"""

from __future__ import annotations

import io

from PIL import Image
from ultralytics import YOLO

from labs.pose_estimation.dto import Keypoint, PoseResult

_MODEL_WEIGHTS = "yolov8n-pose.pt"

# COCO 17 keypoint 순서 — ultralytics pose 모델이 이 순서로 출력한다.
_COCO_KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


class YoloV8PoseAdapter:
    def __init__(self, weights: str = _MODEL_WEIGHTS) -> None:
        self._model = YOLO(weights)

    def estimate(self, image_bytes: bytes) -> list[PoseResult]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        result = self._model.predict(image, verbose=False)[0]

        if result.keypoints is None or result.keypoints.xy.shape[0] == 0:
            return []

        xy = result.keypoints.xy.cpu().numpy()
        conf = result.keypoints.conf.cpu().numpy()
        box_confs = result.boxes.conf.cpu().numpy()

        poses: list[PoseResult] = []
        for person_idx in range(xy.shape[0]):
            keypoints = [
                Keypoint(
                    name=_COCO_KEYPOINT_NAMES[kp_idx],
                    x=float(xy[person_idx][kp_idx][0]),
                    y=float(xy[person_idx][kp_idx][1]),
                    confidence=float(conf[person_idx][kp_idx]),
                )
                for kp_idx in range(len(_COCO_KEYPOINT_NAMES))
            ]
            poses.append(
                PoseResult(
                    keypoints=keypoints, box_confidence=float(box_confs[person_idx])
                )
            )
        return poses
