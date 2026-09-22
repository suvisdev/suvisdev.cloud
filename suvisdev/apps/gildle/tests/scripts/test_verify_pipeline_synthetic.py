"""합성 세계 파이프라인 하네스 — 태양→그림자→그늘→가중치→경로 전 구간 회귀."""

from __future__ import annotations

from gildle.scripts.verify_pipeline_synthetic import HAS_SHAPELY, run_cases


def test_every_case_passes() -> None:
    cases = run_cases()
    failed = [f"{c.name}: {c.detail}" for c in cases if not c.passed and not c.skipped]
    assert not failed, "\n".join(failed)


def test_geometry_cases_run_when_shapely_present() -> None:
    cases = run_cases()
    geometry = [c for c in cases if "그늘" in c.name and "정오" in c.name]
    if HAS_SHAPELY:
        assert geometry and not geometry[0].skipped
    else:
        assert any(c.skipped for c in cases)
