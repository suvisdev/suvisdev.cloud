"""Sentinel 이상 탐지 MCP 서버 — H5의 /api/vision/sentinel/detect HTTP API를 tool로 감싼다.

INFERENCE_URL 환경변수로 추론 API의 base URL을 바꿀 수 있다(온프레미스 기본값,
추후 AWS로 옮겨도 이 값만 바꾸면 됨 — MCP 서버 자체는 HTTP 호출만 하고
ontology 내부 모듈에 직접 의존하지 않는다). image_classifier_mcp_server.py와
동일 패턴.

Usage:
  python -m ontology.adapter.inbound.mcp.anomaly_detection_mcp_server
"""

from __future__ import annotations

import base64
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("suvis-vision-sentinel")

_INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8000")
_DETECT_PATH = "/api/vision/sentinel/detect"


@mcp.tool()
async def detect_anomaly(image_b64: str) -> dict:
    """이미지가 정상 영화 포스터인지, 화질(블러)에 문제가 없는지 판정한다.
    포스터 여부(is_poster/poster_confidence)와 블러 여부(is_blurry/sharpness_score)를
    반환한다. 수집·업로드된 이미지가 포스터가 맞는지, 흐리지 않은지 검수할 때
    사용한다. image_b64는 base64 인코딩된 이미지 바이트다."""
    image_bytes = base64.b64decode(image_b64)
    # 호출당 CLIP 로드(§6.7) — sentiment_analysis와 동일하게 넉넉한 타임아웃
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_INFERENCE_URL}{_DETECT_PATH}",
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        )
        resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    mcp.run()
