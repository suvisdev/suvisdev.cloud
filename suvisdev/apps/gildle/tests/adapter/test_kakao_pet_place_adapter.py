"""카카오 반려동물 장소 어댑터 — 분류·잡음 제거·키 없음(2026-09-28)."""

from __future__ import annotations

from gildle.adapter.outbound.http import kakao_pet_place_adapter as mod
from gildle.domain.value_objects.coordinate import Coordinate


def test_category_mapping():
    assert mod._category({"category_name": "가정,생활 > 반려동물 > 동물병원"}, "펫샵") == "동물병원"
    assert mod._category({"category_name": "음식점 > 카페 > 애견카페"}, "펫샵") == "애견카페"
    assert (
        mod._category({"category_name": "가정,생활 > 반려동물 > 반려동물용품"}, "펫샵") == "용품점"
    )


def test_no_key_returns_empty():
    assert mod.KakaoPetPlaceAdapter(api_key="").search_around(Coordinate(37.5, 127.0), 500) == []


def test_filters_non_pet_noise(monkeypatch):
    docs = [
        {
            "id": "1",
            "place_name": "해피동물병원",
            "category_name": "의료,건강 > 동물병원",
            "x": "127.0",
            "y": "37.5",
        },
        {
            "id": "2",
            "place_name": "강아지떡볶이",
            "category_name": "음식점 > 분식",
            "x": "127.0",
            "y": "37.5",
        },
        {
            "id": "3",
            "place_name": "멍멍용품",
            "category_name": "가정,생활 > 반려동물 > 반려동물용품",
            "x": "127.0",
            "y": "37.5",
        },
    ]

    class _Res:
        def raise_for_status(self) -> None: ...
        def json(self) -> dict:
            return {"documents": docs}

    class _Client:
        def __init__(self, *a, **k) -> None: ...
        def __enter__(self):
            return self

        def __exit__(self, *a) -> None: ...
        def get(self, *a, **k):
            return _Res()

    monkeypatch.setattr(mod.httpx, "Client", _Client)
    places = mod.KakaoPetPlaceAdapter(api_key="k").search_around(Coordinate(37.5, 127.0), 500)
    assert sorted(p.name for p in places) == ["멍멍용품", "해피동물병원"]
