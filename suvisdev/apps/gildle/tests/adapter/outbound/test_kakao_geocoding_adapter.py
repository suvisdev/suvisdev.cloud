import gildle.adapter.outbound.geocoding.kakao_geocoding_adapter as kakao_module
from gildle.adapter.outbound.geocoding.kakao_geocoding_adapter import (
    KakaoGeocodingAdapter,
)
from gildle.domain.value_objects.coordinate import Coordinate


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class TestKakaoGeocodingAdapter:
    def test_returns_none_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("KAKAO_API_KEY", raising=False)
        adapter = KakaoGeocodingAdapter()

        assert adapter.geocode("서울 영등포구 여의대로") is None

    def test_successful_geocode_returns_coordinate(self, monkeypatch):
        monkeypatch.setenv("KAKAO_API_KEY", "test-key")
        payload = {"documents": [{"x": "126.924", "y": "37.521"}]}
        monkeypatch.setattr(
            kakao_module.httpx, "get", lambda *a, **k: _FakeResponse(payload)
        )
        adapter = KakaoGeocodingAdapter()

        result = adapter.geocode("서울 영등포구 여의대로")

        assert result == Coordinate(latitude=37.521, longitude=126.924)

    def test_no_documents_returns_none(self, monkeypatch):
        monkeypatch.setenv("KAKAO_API_KEY", "test-key")
        monkeypatch.setattr(
            kakao_module.httpx, "get", lambda *a, **k: _FakeResponse({"documents": []})
        )
        adapter = KakaoGeocodingAdapter()

        assert adapter.geocode("없는 주소") is None

    def test_request_error_returns_none(self, monkeypatch):
        monkeypatch.setenv("KAKAO_API_KEY", "test-key")

        def _boom(*a, **k):
            raise RuntimeError("network down")

        monkeypatch.setattr(kakao_module.httpx, "get", _boom)
        adapter = KakaoGeocodingAdapter()

        assert adapter.geocode("서울역") is None
