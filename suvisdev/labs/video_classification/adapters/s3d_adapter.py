"""S3D(torchvision, Kinetics-400) 어댑터 — VideoClassificationPort 구현체.

사전학습 가중치는 최초 실행 시 torch hub가 자동으로 다운로드한다(인터넷
필요, 이후엔 `~/.cache/torch/hub/checkpoints/`에 캐시돼 재사용). 학습은
하지 않고 사전학습 모델 추론만 한다 — GPU 없는 환경(CPU-only)을 전제로
torchvision.models.video 중 가장 가벼운 s3d(약 8.3M 파라미터)를 쓴다.
"""

from __future__ import annotations

import tempfile

import cv2
import numpy as np
import torch
from torchvision.models.video import S3D_Weights, s3d

from labs.video_classification.dto import LabelScore, VideoClassificationResult

_NUM_FRAMES = 16


class S3DVideoClassificationAdapter:
    def __init__(self) -> None:
        weights = S3D_Weights.DEFAULT
        self._model = s3d(weights=weights)
        self._model.eval()
        self._preprocess = weights.transforms()
        self._categories = weights.meta["categories"]

    def classify(self, video_bytes: bytes, *, top_k: int = 5) -> VideoClassificationResult:
        frames = self._read_frames(video_bytes)
        clip = self._sample_frames(frames, _NUM_FRAMES)
        video = torch.stack(clip)  # (T, C, H, W)
        batch = self._preprocess(video).unsqueeze(0)

        with torch.no_grad():
            logits = self._model(batch)
        probs = logits.softmax(dim=1)[0]
        k = min(top_k, len(self._categories))
        scores, indices = torch.topk(probs, k)

        predictions = [
            LabelScore(label=self._categories[idx], score=float(score))
            for score, idx in zip(scores, indices)
        ]
        return VideoClassificationResult(predictions=predictions)

    @staticmethod
    def _read_frames(video_bytes: bytes) -> list[torch.Tensor]:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(video_bytes)
            tmp.flush()
            cap = cv2.VideoCapture(tmp.name)
            frames: list[torch.Tensor] = []
            try:
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(torch.from_numpy(frame_rgb).permute(2, 0, 1))
            finally:
                cap.release()
        if not frames:
            raise ValueError("영상에서 프레임을 읽지 못했습니다.")
        return frames

    @staticmethod
    def _sample_frames(frames: list[torch.Tensor], num_frames: int) -> list[torch.Tensor]:
        if len(frames) <= num_frames:
            return frames
        indices = np.linspace(0, len(frames) - 1, num_frames).round().astype(int)
        return [frames[i] for i in indices]
