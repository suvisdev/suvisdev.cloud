"""H6 — 포스터 장르 분류 MCP tool을 온프레미스 Ollama(qwen2.5)에 연결하는 에이전트.

실측 결과 qwen2.5:1.5b는 tool_calls를 신뢰성 있게 생성하지 않아(소형 모델 한계),
tool 호출 트리거는 결정적 규칙(이미지가 첨부되면 항상 classify_image 호출)으로
처리하고, LLM은 그 결과를 자연어로 요약하는 역할만 맡는다. 문서 H6의 skill
규칙(이미지 질문이면 tool 사용 / confidence<0.6이면 불확실 명시 / 지원 클래스
불확실하면 list_supported_classes 우선 확인)은 이 규칙 기반 오케스트레이션으로
그대로 구현된다.
"""

from __future__ import annotations

import base64
import os
from typing import Any, cast

import httpx

_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.getenv("VISION_AGENT_MODEL", "qwen2.5:1.5b")
_INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8000")
_CONFIDENCE_THRESHOLD = 0.6

_SYSTEM_PROMPT = """너는 이미지 분류 에이전트다.
- 분류 결과(top-3 장르와 신뢰도)가 주어지면 사용자 친화적으로 한국어로 요약해 전달한다.
- top-1 confidence가 낮다고 표시되어 있으면 "확실하지 않다"고 명시하고 상위 후보를 함께 제시한다.
- 결과는 짧고 자연스럽게 설명한다."""


async def _classify_via_api(image_bytes: bytes) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{_INFERENCE_URL}/api/vision/genre/classify",
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        )
        resp.raise_for_status()
    return cast(list[dict[str, Any]], resp.json())


async def _summarize_with_llm(user_message: str, predictions: list[dict[str, Any]]) -> str:
    top1_confidence = predictions[0]["confidence"] if predictions else 0.0
    uncertain = top1_confidence < _CONFIDENCE_THRESHOLD

    result_text = "\n".join(f"- {p['label']}: {p['confidence']:.1%}" for p in predictions)
    prompt = (
        f"사용자 질문: {user_message}\n"
        f"분류 결과(top-3):\n{result_text}\n"
        f"top-1 신뢰도 낮음(불확실): {uncertain}\n"
        "위 결과를 바탕으로 사용자에게 답해라."
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_OLLAMA_URL}/api/chat",
            json={
                "model": _OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        resp.raise_for_status()
    return cast(str, resp.json()["message"]["content"])


async def answer_image_question(user_message: str, image_bytes: bytes) -> str:
    """이미지가 첨부된 사용자 질문에 대해 classify_image 결과 기반으로 자연어 답변을 만든다."""
    predictions = await _classify_via_api(image_bytes)
    return await _summarize_with_llm(user_message, predictions)


if __name__ == "__main__":
    import asyncio
    import sys

    image_path = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else "이 포스터 무슨 장르야?"
    image_bytes = base64.b64decode(base64.b64encode(open(image_path, "rb").read()))
    answer = asyncio.run(answer_image_question(question, image_bytes))
    print(answer)
