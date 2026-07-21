"""포스터 장르 분류 MCP 서버 — H4의 /api/vision/genre/* HTTP API를 tool로 감싼다.

INFERENCE_URL 환경변수로 추론 API의 base URL을 바꿀 수 있다(온프레미스 기본값,
추후 AWS로 옮겨도 이 값만 바꾸면 됨 — MCP 서버 자체는 HTTP 호출만 하고
ontology 내부 모듈에 직접 의존하지 않는다).

Usage:
  python -m ontology.adapter.inbound.mcp.image_classifier_mcp_server
"""

from __future__ import annotations

import base64
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("suvis-vision-genre")

_INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8000")
_CLASSIFY_PATH = "/api/vision/genre/classify"
_CLASSES_PATH = "/api/vision/genre/classes"


@mcp.tool()
async def classify_image(image_b64: str) -> dict:
    """영화 포스터 이미지를 분류해 top-3 장르와 신뢰도를 반환한다.
    사용자가 '이 포스터 무슨 장르야', '이 사진 뭐야' 등 이미지 내용을
    물을 때 사용한다. image_b64는 base64 인코딩된 이미지 바이트다."""
    image_bytes = base64.b64decode(image_b64)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{_INFERENCE_URL}{_CLASSIFY_PATH}",
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        )
        resp.raise_for_status()
    return {"predictions": resp.json()}


@mcp.tool()
async def list_supported_classes() -> list[str]:
    """이 분류기가 인식 가능한 장르 클래스 목록을 반환한다.
    지원 여부가 불확실할 때 classify_image보다 먼저 호출한다."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_INFERENCE_URL}{_CLASSES_PATH}")
        resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    mcp.run()
