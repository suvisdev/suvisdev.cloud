"""출처별 요청 속도 — 예매 폭주·어뷰징의 1차 신호. DB를 거치지 않아 빠르다.

이벤트 루프 스레드에서만 호출되므로 잠금이 없다. replicas 1 전제(토큰 jti와 같은 이유).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from deolmi.app.ports.output.velocity_port import VelocityPort

_PRUNE_THRESHOLD = 10_000


class SlidingWindowVelocityAdapter(VelocityPort):
    def __init__(self, window_s: float = 10.0) -> None:
        self._window = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def record(self, key: str) -> int:
        now = time.monotonic()
        cutoff = now - self._window
        dq = self._hits[key]
        dq.append(now)
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(self._hits) > _PRUNE_THRESHOLD:  # 위조 키가 쌓여도 메모리가 계속 늘지 않게
            for k in [k for k, d in self._hits.items() if not d or d[-1] < cutoff]:
                del self._hits[k]
        return len(dq)
