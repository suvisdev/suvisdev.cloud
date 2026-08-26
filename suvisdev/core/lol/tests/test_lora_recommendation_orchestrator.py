from __future__ import annotations

import httpx
import pytest

from core.lol import lora_recommendation_orchestrator as module
from core.lol.lora_recommendation_orchestrator import (
    LoraOrchestratorError,
    LoraRecommendationOrchestrator,
)


class _FakeResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json_data


def _fake_client_class(results: list, calls: list[dict]):
    """httpx.Client(...) 대체 — post() 호출마다 results를 순서대로 소비한다.
    예외 객체면 raise, 아니면 그대로 반환(HTTP 응답 흉내)."""

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> bool:
            return False

        def post(self, url, json=None, headers=None):
            calls.append({"url": url, "json": json, "headers": headers})
            result = results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

    return _FakeClient


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """재시도 backoff(0.5s)만큼 테스트가 실제로 기다리지 않게 한다."""
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)


@pytest.fixture(autouse=True)
def _reset_circuit(monkeypatch):
    """서킷 브레이커 전역 상태가 앞선 실패 테스트에서 누출되지 않게 매 테스트 초기화."""
    monkeypatch.setattr(module, "_circuit_failures", 0)
    monkeypatch.setattr(module, "_circuit_open_until", 0.0)


def _orchestrator(**kwargs) -> LoraRecommendationOrchestrator:
    return LoraRecommendationOrchestrator(base_url="http://lora.test", **kwargs)


def test_generate_success_first_try(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(
        module.httpx,
        "Client",
        _fake_client_class([_FakeResponse(json_data={"text": "hello"})], calls),
    )
    orch = _orchestrator()
    assert orch.generate("prompt") == "hello"
    assert len(calls) == 1


def test_generate_retries_once_on_timeout_then_succeeds(monkeypatch):
    calls: list[dict] = []
    results = [httpx.TimeoutException("timeout"), _FakeResponse(json_data={"text": "ok"})]
    monkeypatch.setattr(module.httpx, "Client", _fake_client_class(results, calls))
    orch = _orchestrator()
    assert orch.generate("prompt") == "ok"
    assert len(calls) == 2


def test_generate_fails_after_retry_exhausted_on_transport_error(monkeypatch):
    calls: list[dict] = []
    results = [httpx.ConnectError("boom"), httpx.ConnectError("boom again")]
    monkeypatch.setattr(module.httpx, "Client", _fake_client_class(results, calls))
    orch = _orchestrator()
    with pytest.raises(LoraOrchestratorError) as exc_info:
        orch.generate("prompt")
    assert exc_info.value.status_code == 503
    assert len(calls) == 2  # 최초 시도 + 1회 재시도, 그 이상은 없음


def test_generate_does_not_retry_on_http_error_status(monkeypatch):
    """HTTP 응답 자체는 왔지만 상태코드가 5xx면 재시도하지 않고 즉시 실패한다."""
    calls: list[dict] = []
    results = [_FakeResponse(status_code=500, text="server error")]
    monkeypatch.setattr(module.httpx, "Client", _fake_client_class(results, calls))
    orch = _orchestrator()
    with pytest.raises(LoraOrchestratorError) as exc_info:
        orch.generate("prompt")
    assert exc_info.value.status_code == 502
    assert len(calls) == 1


def test_generate_attaches_token_header_when_configured(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(
        module.httpx,
        "Client",
        _fake_client_class([_FakeResponse(json_data={"text": "hi"})], calls),
    )
    orch = _orchestrator(token="secret-token")
    orch.generate("prompt")
    assert calls[0]["headers"] == {"X-LoRA-Token": "secret-token"}


def test_generate_omits_token_header_when_not_configured(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(
        module.httpx,
        "Client",
        _fake_client_class([_FakeResponse(json_data={"text": "hi"})], calls),
    )
    orch = _orchestrator(token="")
    orch.generate("prompt")
    assert calls[0]["headers"] == {}
