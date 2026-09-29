"""월별 그늘 표 선택 — 오늘 날짜에 가장 가까운 달, 없으면 구 단일 표(2026-09-29)."""

from __future__ import annotations

import json
from datetime import date

import pytest

pytest.importorskip("fastapi")

from gildle.adapter.inbound.api.v1 import route_router as rr  # noqa: E402


def _table(path, month_date, pct):
    path.write_text(
        json.dumps({"date": month_date, "slots": [12], "edges": {"a-b": [pct]}}), encoding="utf-8"
    )


def test_picks_nearest_month_and_falls_back_to_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(rr, "_DATA_DIR", tmp_path)
    monkeypatch.delenv("GILDLE_SHADE_SCORES", raising=False)
    rr._shade_cache.clear()
    rr._shade_lookup_by_slot.clear()
    assert rr._shade_path(date(2026, 9, 29)) is None  # 표가 없음

    _table(tmp_path / "shade_scores.json", "2026-08-01", 10)
    assert rr._shade_path(date(2026, 12, 1)).name == "shade_scores.json"  # 월별 없으면 구 표

    _table(tmp_path / "shade_scores_08.json", "2026-08-15", 20)
    _table(tmp_path / "shade_scores_12.json", "2026-12-15", 80)
    assert rr._shade_path(date(2026, 9, 29)).name == "shade_scores_08.json"
    assert rr._shade_path(date(2026, 11, 3)).name == "shade_scores_12.json"
    assert rr._shade_path(date(2026, 2, 1)).name == "shade_scores_12.json"  # 12월↔2월은 원형 거리 2

    # 표마다 lookup 캐시가 따로 — 12월 표의 그늘 80%가 8월 값(20%)으로 섞이지 않는다
    dec = rr._load_shade_scores(date(2026, 12, 20))
    aug = rr._load_shade_scores(date(2026, 8, 3))
    assert rr._build_shade_lookup(12, dec)[("a", "b")] == 0.8
    assert rr._build_shade_lookup(12, aug)[("a", "b")] == 0.2


def test_env_override_wins(tmp_path, monkeypatch):
    monkeypatch.setattr(rr, "_DATA_DIR", tmp_path)
    _table(tmp_path / "shade_scores_08.json", "2026-08-15", 20)
    custom = tmp_path / "custom.json"
    _table(custom, "2026-01-01", 5)
    monkeypatch.setenv("GILDLE_SHADE_SCORES", str(custom))
    assert rr._shade_path(date(2026, 8, 1)) == custom
