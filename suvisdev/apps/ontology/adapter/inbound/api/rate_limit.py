"""간단한 인메모리 rate limit — 공개(무인증) LLM 엔드포인트의 호출 비용 방어.

`apps/mova/adapter/inbound/api/rate_limit.py`의 복제본(2026-09-27). mova는 Spoke라 Hub(ontology)가
import할 수 없고(.importlinter Rule 1·2), `ollama_embedding_adapter.py`가 dispatch 것을 복제했던 것과
같은 선택이다. 프로세스 로컬 고정 윈도우 카운터 — 멀티 워커 간 공유되지 않고 재시작 시 초기화된다
(비용 폭주 완화가 목적, 정밀 분산 제한이 아님).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 20
_PRUNE_THRESHOLD = 10_000  # 위조 키로 메모리가 무한히 늘지 않게 주기적으로 비운다
_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    # Cloudflare 경유면 CF-Connecting-IP가 실제 클라이언트. X-Forwarded-For는 "첫" 요소가
    # 위조 가능하므로 프록시가 마지막에 붙인 요소를 쓴다.
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
