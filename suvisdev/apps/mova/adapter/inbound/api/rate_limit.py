"""간단한 인메모리 rate limit — /mova/chat Gemini 호출 비용 방어.

프로세스 로컬 고정 윈도우 카운터. 멀티 워커 간 공유되지 않고 재시작 시 초기화된다
(비용 폭주 완화가 목적, 정밀 분산 제한이 아님). 필요 시 Redis 등으로 대체 가능.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 20

_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def chat_rate_limit(request: Request) -> None:
    """윈도우 내 IP당 호출 수 초과 시 429."""
    now = time.monotonic()
    bucket = _hits[_client_key(request)]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _MAX_REQUESTS:
        retry_after = int(_WINDOW_SECONDS - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도하세요.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)
