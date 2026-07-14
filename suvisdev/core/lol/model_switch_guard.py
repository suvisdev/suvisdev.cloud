"""Ollama 모델 교체 시 이전 모델의 VRAM 언로드를 폴링으로 확인하는 공용 가드."""

from __future__ import annotations

import time

import httpx


def wait_until_model_unloaded(
    base_url: str,
    model: str,
    *,
    timeout: float = 10.0,
    poll_interval: float = 0.3,
) -> bool:
    """`/api/ps`를 폴링해 model이 로드 목록에서 사라질 때까지 대기한다.

    timeout 내에 사라지면 True, 넘어가면 False를 반환한다 (호출자가 로그·재시도 판단).
    """
    base_url = base_url.rstrip("/")
    deadline = time.monotonic() + timeout

    while True:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{base_url}/api/ps")
                loaded = {m["model"] for m in r.json().get("models", [])}
        except httpx.TransportError:
            return False

        if model not in loaded:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)
