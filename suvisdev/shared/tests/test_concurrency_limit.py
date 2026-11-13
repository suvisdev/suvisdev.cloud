"""동시 처리 상한 — 자리가 차면 기다렸다 503, 끝나거나 실패하면 자리를 돌려준다."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import Depends, FastAPI
from shared.security.concurrency_limit import ConcurrencyLimit


def _app(limit: ConcurrencyLimit, gate: asyncio.Event) -> FastAPI:
    app = FastAPI()

    @app.post("/chat")
    async def chat(fail: bool = False, _b: None = Depends(limit)) -> dict[str, bool]:
        await gate.wait()  # LLM 응답을 기다리는 동안 자리를 쥐고 있다
        if fail:
            raise RuntimeError("LLM 실패")
        return {"ok": True}

    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://t")


@pytest.mark.asyncio
async def test_full_slots_wait_then_503_and_free_after_finish():
    gate = asyncio.Event()
    async with _client(_app(ConcurrencyLimit(max_concurrent=2, wait_seconds=0.2), gate)) as c:
        running = [asyncio.create_task(c.post("/chat")) for _ in range(2)]
        await asyncio.sleep(0.05)
        busy = await c.post("/chat")
        assert busy.status_code == 503 and busy.headers["Retry-After"] == "10"
        gate.set()
        assert [r.status_code for r in await asyncio.gather(*running)] == [200, 200]
        assert (await c.post("/chat")).status_code == 200


@pytest.mark.asyncio
async def test_waiting_request_gets_slot_when_one_frees_in_time():
    gate = asyncio.Event()
    async with _client(_app(ConcurrencyLimit(max_concurrent=1, wait_seconds=2.0), gate)) as c:
        first = asyncio.create_task(c.post("/chat"))
        await asyncio.sleep(0.05)
        second = asyncio.create_task(c.post("/chat"))
        await asyncio.sleep(0.1)
        gate.set()
        assert [(await first).status_code, (await second).status_code] == [200, 200]


@pytest.mark.asyncio
async def test_failed_request_returns_its_slot():
    gate = asyncio.Event()
    gate.set()
    async with _client(_app(ConcurrencyLimit(max_concurrent=1, wait_seconds=0.2), gate)) as c:
        assert (await c.post("/chat", params={"fail": True})).status_code == 500
        assert (await c.post("/chat")).status_code == 200
