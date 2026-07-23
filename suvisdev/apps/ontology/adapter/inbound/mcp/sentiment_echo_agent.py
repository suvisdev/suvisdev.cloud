"""H6 — 감정 분석 MCP tool을 온프레미스 Ollama(EXAONE-3.5-2.4B)에 연결하는 에이전트.

vision_genre_agent.py와 동일한 오케스트레이션 패턴(소형 모델은 tool_calls를
신뢰성 있게 생성하지 않으므로, tool 호출 트리거는 결정적 규칙(텍스트가 주어지면
항상 analyze_sentiment 호출)으로 처리하고 LLM은 결과를 자연어로 요약하는 역할만
맡는다)을 따르되, 요약 LLM은 문서 상단의 사용자 결정(2026-07-22: 생성형 모델은
Qwen 대신 EXAONE-3.5-2.4B-Instruct로 고정)에 맞춰 exaone3.5:2.4b를 쓴다.

Echo는 긍정/부정 2-클래스만 학습됐고(H2, NSMC에 중립 라벨 없음) reason은 생성하지
않으므로(H4, logit만 비교) 문서 H6 초안의 "중립/혼합 표시", "문장별 분해" 규칙은
시스템 프롬프트에서 제외했다 — tool이 뒷받침 못하는 지시를 LLM에 주면 실제
반환값과 어긋나는 응답(할루시네이션)을 유도하게 된다.
"""

from __future__ import annotations

import os

import httpx

_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.getenv("SENTIMENT_AGENT_MODEL", "exaone3.5:2.4b")
_INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8000")
_CONFIDENCE_THRESHOLD = 0.6

_SYSTEM_PROMPT = """너는 감정 분석 에이전트 Echo다.
- 분석 결과(극성과 신뢰도)가 주어지면 사용자 친화적으로 한국어로 요약해 전달한다.
- 신뢰도가 낮다고 표시되어 있으면 "확실하지 않다"고 명시한다.
- 결과는 짧고 자연스럽게 설명한다."""


async def _analyze_via_api(text: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_INFERENCE_URL}/api/nlp/sentiment/analyze",
            json={"text": text},
        )
        resp.raise_for_status()
    return resp.json()


async def _summarize_with_llm(user_message: str, result: dict) -> str:
    uncertain = result["score"] < _CONFIDENCE_THRESHOLD

    prompt = (
        f"사용자 텍스트: {user_message}\n"
        f"분석 결과: 극성={result['label']}, 신뢰도={result['score']:.1%}\n"
        f"신뢰도 낮음(불확실): {uncertain}\n"
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
    return resp.json()["message"]["content"]


async def answer_sentiment_question(text: str) -> str:
    """텍스트에 대해 analyze_sentiment 결과 기반으로 자연어 답변을 만든다."""
    result = await _analyze_via_api(text)
    return await _summarize_with_llm(text, result)


if __name__ == "__main__":
    import asyncio
    import sys

    text = sys.argv[1]
    answer = asyncio.run(answer_sentiment_question(text))
    print(answer)
