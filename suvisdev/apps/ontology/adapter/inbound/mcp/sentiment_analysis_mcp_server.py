"""Echo 감정 분석 MCP 서버 — H5의 /api/nlp/sentiment/analyze HTTP API를 tool로 감싼다.

INFERENCE_URL 환경변수로 추론 API의 base URL을 바꿀 수 있다(온프레미스 기본값,
추후 AWS로 옮겨도 이 값만 바꾸면 됨 — MCP 서버 자체는 HTTP 호출만 하고
ontology 내부 모듈에 직접 의존하지 않는다). image_classifier_mcp_server.py와
동일 패턴.

Usage:
  python -m ontology.adapter.inbound.mcp.sentiment_analysis_mcp_server
"""

from __future__ import annotations

import os
from typing import Any, cast

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("suvis-sentiment-echo")

_INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8000")
_ANALYZE_PATH = "/api/nlp/sentiment/analyze"


@mcp.tool()
async def analyze_sentiment(text: str) -> dict[str, Any]:
    """텍스트의 감정을 분석해 극성(긍정/부정)과 신뢰도를 반환한다.
    리뷰·댓글·문장의 감정을 물을 때 사용한다."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{_INFERENCE_URL}{_ANALYZE_PATH}", json={"text": text})
        resp.raise_for_status()
    return cast(dict[str, Any], resp.json())


if __name__ == "__main__":
    mcp.run()
