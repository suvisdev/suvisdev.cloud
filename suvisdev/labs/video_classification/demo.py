"""08(영상 분류) labs 데모 — 학습 없이 사전학습 S3D로 합성 클립 1개 추론.

이 저장소엔 실제 동영상 샘플이 없어서, samples/source.jpg(ultralytics 기본
내장 bus.jpg)를 살짝 확대·회전시키며 여러 프레임으로 늘린 "합성 클립"을
매 실행 즉석에서 만든다 — 진짜 동작(action)이 없는 가짜 움직임이라 분류
결과는 의미 있는 정답이 아니라 **파이프라인이 끝까지 도는지 확인용**이다.
실제 편입 시에는 이 부분을 진짜 영상 입력으로 교체한다.

사전학습 가중치(s3d Kinetics-400)는 최초 실행 시 torch hub가 자동
다운로드한다(인터넷 필요, 이후엔 ~/.cache/torch/hub/checkpoints/ 재사용).

실행: python -m labs.video_classification.demo
"""

from __future__ import annotations

from pathlib import Path

import cv2

from labs.video_classification.adapters.s3d_adapter import S3DVideoClassificationAdapter

_SOURCE_IMAGE = Path(__file__).parent / "samples" / "source.jpg"
_NUM_FRAMES = 16


def _build_synthetic_clip(image_path: Path, num_frames: int) -> bytes:
    """정지 이미지를 살짝 확대하며 여러 프레임으로 늘려 mp4 바이트를 만든다."""
    image = cv2.imread(str(image_path))
    h, w = image.shape[:2]

    tmp_path = "/tmp/labs_video_classification_synthetic.mp4"
    writer = cv2.VideoWriter(tmp_path, cv2.VideoWriter_fourcc(*"mp4v"), 8, (w, h))
    for i in range(num_frames):
        scale = 1.0 + i * 0.01
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), 0, scale)
        frame = cv2.warpAffine(image, matrix, (w, h))
        writer.write(frame)
    writer.release()

    return Path(tmp_path).read_bytes()


def main() -> None:
    video_bytes = _build_synthetic_clip(_SOURCE_IMAGE, _NUM_FRAMES)
    adapter = S3DVideoClassificationAdapter()
    result = adapter.classify(video_bytes, top_k=5)

    print(
        f"(합성 클립, 실제 동작 없음 — 파이프라인 확인용) top-{len(result.predictions)} 예측:"
    )
    for pred in result.predictions:
        print(f"  {pred.label:30s} {pred.score:.3f}")


if __name__ == "__main__":
    main()
