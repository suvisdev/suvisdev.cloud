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
# 위조 키가 쌓여도 메모리가 계속 늘지 않게, 키가 이 수를 넘으면 만료 버킷을 정리
_PRUNE_THRESHOLD = 10_000

_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    # Cloudflare(cloudflared) 뒤에서는 CF-Connecting-IP가 신뢰 가능한 원 IP.
    # X-Forwarded-For의 "첫" 요소는 클라이언트가 헤더를 직접 붙여 위조할 수
    # 있어(요청마다 난수 → IP당 제한 완전 우회, 2026-09-11 리뷰) 마지막
    # 요소(가장 가까운 프록시가 기록한 값)를 쓴다.
    cf_ip = request.headers.get("cf-connecting-ip", "").strip()
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def chat_rate_limit(request: Request) -> None:
    """윈도우 내 IP당 호출 수 초과 시 429."""
    now = time.monotonic()
    if len(_hits) > _PRUNE_THRESHOLD:
        for stale_key in [k for k, b in _hits.items() if not b or now - b[-1] > _WINDOW_SECONDS]:
            del _hits[stale_key]
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
