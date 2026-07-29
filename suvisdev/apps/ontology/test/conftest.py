"""ontology 테스트 전용 conftest — HF Hub 모델 로드를 오프라인으로 강제.

@pytest.mark.gpu 테스트(sentinel_anomaly/echo_sentiment 어댑터)는 로컬에 이미
캐시된 CLIP/NSMC 모델만 쓴다는 전제다(각 테스트 파일 주석 참고). 온라인 모드로
두면 캐시가 있어도 `from_pretrained()`가 매번 HF Hub에 etag 확인·재개 다운로드를
시도하는데, 네트워크가 불안정하면(2026-07-28: CLIP 블롭이 `.incomplete`로 멈춘
채 남아있던 사례 확인 — `~/.cache/huggingface/hub/models--openai--clip-vit-base-patch32/
blobs/*.incomplete`, 490MB 그대로 정체) huggingface_hub의 재시도가 길게
늘어져 테스트 스위트 전체가 hang 상태로 보인다.

HF_HUB_OFFLINE으로 네트워크 경로 자체를 막으면 "캐시 있으면 즉시 통과,
없으면 즉시 에러"로 바뀐다 — huggingface_hub.constants가 이 값을 import 시점에
한 번만 읽으므로, transformers를 임포트하는 어떤 테스트 모듈보다도 먼저
로드되는 conftest.py에서 설정해야 한다.
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
