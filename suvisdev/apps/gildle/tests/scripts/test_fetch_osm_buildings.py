"""건물 수집 스크립트의 순수 부품 검증(높이 결정·타일 분할)."""

from __future__ import annotations

from gildle.scripts.fetch_osm_buildings import make_tiles, resolve_height_m


def test_height_tag_priority():
    assert resolve_height_m({"height": "25", "building:levels": "3"}) == (25.0, True)


def test_height_tag_with_unit_suffix():
    assert resolve_height_m({"height": "25 m"}) == (25.0, True)


def test_levels_fallback():
    assert resolve_height_m({"building:levels": "5"}) == (15.0, True)  # 5층 × 3.0m


def test_default_height_is_unknown():
    assert resolve_height_m({}) == (6.0, False)


def test_broken_tags_fall_back_to_default():
    assert resolve_height_m({"height": "abc", "building:levels": "?"}) == (6.0, False)


def test_negative_height_treated_as_unknown():
    # 서울 실측에서 -6.0 등 발견(2026-08-27) — 오염 데이터는 기본값·결측 처리.
    assert resolve_height_m({"height": "-6"}) == (6.0, False)
    assert resolve_height_m({"building:levels": "0"}) == (6.0, False)


def test_make_tiles_covers_bbox():
    tiles = make_tiles(37.0, 127.0, 37.05, 127.03, step=0.02)
    assert len(tiles) == 3 * 2  # lat 3칸 × lng 2칸(올림)
    assert tiles[0] == (37.0, 127.0, 37.02, 127.02)
    last = tiles[-1]
    assert last[2] >= 37.05 and last[3] >= 127.03
