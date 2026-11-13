"""요청 제한 — 실제 Redis에서 Lua 스크립트까지 돈다. CI는 Redis 서비스를 띄워 RATE_LIMIT_TEST_REDIS_URL을 준다.

운영 Redis를 건드리지 않게 기본 REDIS_URL은 쓰지 않는다. 변수가 없으면 Redis가 필요한 시험은 건너뛴다.
"""

from __future__ import annotations

import os
import time
import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from shared.security.rate_limit import RateLimit

REDIS_URL = os.getenv("RATE_LIMIT_TEST_REDIS_URL")
needs_redis = pytest.mark.skipif(not REDIS_URL, reason="RATE_LIMIT_TEST_REDIS_URL 없음")


def _client(limit: RateLimit) -> TestClient:
    app = FastAPI()

    @app.post("/chat")
    def chat(_r: None = Depends(limit)) -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def _post(client: TestClient, ip: str) -> int:
    return client.post("/chat", headers={"cf-connecting-ip": ip}).status_code


def _scope() -> str:  # 시험마다 새 키 — 이전 실행이 남긴 카운트와 섞이지 않게
    return f"test-{uuid.uuid4().hex}"


@needs_redis
def test_twenty_per_ip_then_429_with_retry_after():
    client = _client(RateLimit(_scope(), redis_url=REDIS_URL))
    assert [_post(client, "1.1.1.1") for _ in range(20)] == [200] * 20
    res = client.post("/chat", headers={"cf-connecting-ip": "1.1.1.1"})
    assert res.status_code == 429 and 1 <= int(res.headers["Retry-After"]) <= 60
    assert _post(client, "2.2.2.2") == 200  # 다른 IP는 따로 센다


@needs_redis
def test_count_survives_restart_and_scopes_are_separate():
    scope = _scope()
    first = _client(RateLimit(scope, redis_url=REDIS_URL))
    for _ in range(15):
        first.post("/chat", headers={"cf-connecting-ip": "3.3.3.3"})
    restarted = _client(RateLimit(scope, redis_url=REDIS_URL))  # backend 재배포와 같다
    assert [_post(restarted, "3.3.3.3") for _ in range(6)] == [200] * 5 + [429]
    other = _client(RateLimit(_scope(), redis_url=REDIS_URL))  # 홈 채팅과 mova 채팅은 각자 센다
    assert _post(other, "3.3.3.3") == 200


@needs_redis
def test_window_slides_instead_of_resetting_at_boundary():
    # 최근 N초 창이라 가장 오래된 요청이 창 밖으로 나간 만큼만 다시 열린다(고정 창이면 한 번에 다 열린다).
    client = _client(RateLimit(_scope(), max_requests=2, window_seconds=2, redis_url=REDIS_URL))
    assert _post(client, "4.4.4.4") == 200
    time.sleep(1.2)
    assert _post(client, "4.4.4.4") == 200
    assert _post(client, "4.4.4.4") == 429
    time.sleep(1.0)  # 첫 요청만 창 밖 → 한 자리
    assert _post(client, "4.4.4.4") == 200
    assert _post(client, "4.4.4.4") == 429


def test_redis_down_blocks_with_503():
    client = _client(RateLimit(_scope(), redis_url="redis://127.0.0.1:1/0"))
    assert _post(client, "5.5.5.5") == 503
