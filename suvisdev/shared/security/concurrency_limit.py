"""공개 LLM 엔드포인트의 동시 처리 상한 — 자리가 없으면 잠깐 기다리고, 그래도 없으면 503.

2026-11-13 실측: 노트북 올라마 7.8B는 요청을 하나씩 처리해 동시 6개면 응답이 4.6초~16.2초로 줄을 선다.
홈 채팅의 올라마 제한 시간(40초)을 넘긴 요청은 Gemini로 넘어가 무료 할당량까지 쓴다. 줄을 끝없이 세우지 않고
"지금 붐빈다"를 빨리 돌려준다. 요청 제한(rate_limit.py)이 IP별 속도라면 이것은 엔드포인트 전체의 동시 수다.

ponytail: 프로세스 안 세마포어 — backend는 파드 1개·워커 1개라 충분하다. 늘리면 Redis 세마포어로 옮긴다.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import HTTPException


class ConcurrencyLimit:
    """FastAPI yield 의존성. 라우터에서 RateLimit 뒤에 둔다(429 요청이 자리를 차지하지 않게)."""

    def __init__(self, *, max_concurrent: int = 3, wait_seconds: float = 10.0) -> None:
        self._slots = asyncio.Semaphore(max_concurrent)
        self._wait = wait_seconds

    async def __call__(self) -> AsyncIterator[None]:
        try:
            await asyncio.wait_for(self._slots.acquire(), self._wait)
        except TimeoutError:
            raise HTTPException(
                status_code=503,
                detail="지금 대화가 많아요. 잠시 후 다시 시도해 주세요.",
                headers={"Retry-After": "10"},
            ) from None
        try:
            yield
        finally:
            self._slots.release()
