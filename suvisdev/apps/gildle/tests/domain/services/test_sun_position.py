"""태양 위치 근사 검증 — 서울 한여름 실측 근사값(허용 오차 포함)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from gildle.domain.services.sun_position import sun_altitude_azimuth

_SEOUL_LAT = 37.5665
_SEOUL_LNG = 126.9780
_KST = timezone(timedelta(hours=9))


def _kst(hour: int, minute: int = 0) -> datetime:
    # 2026-08-01 KST 기준. 함수가 내부에서 UTC로 변환한다.
    return datetime(2026, 8, 1, hour, minute, tzinfo=_KST)


def test_noon_high_altitude_south():
    alt, az = sun_altitude_azimuth(_SEOUL_LAT, _SEOUL_LNG, _kst(12, 30))
    assert 66.0 <= alt <= 76.0  # 한여름 남중 고도 근사
    assert 150.0 <= az <= 210.0  # 남쪽


def test_morning_low_altitude_east():
    alt, az = sun_altitude_azimuth(_SEOUL_LAT, _SEOUL_LNG, _kst(8))
    assert 20.0 <= alt <= 40.0
    assert 60.0 <= az <= 110.0  # 동쪽


def test_night_negative_altitude():
    alt, _ = sun_altitude_azimuth(_SEOUL_LAT, _SEOUL_LNG, _kst(23))
    assert alt < 0.0
