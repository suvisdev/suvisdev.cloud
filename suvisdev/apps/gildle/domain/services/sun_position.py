"""태양 고도·방위각 근사 계산 — 순수 수식(NOAA 간이 알고리즘).

외부 라이브러리·네트워크 의존 없음. 그늘 배치 계산이 시간 슬롯별 태양
위치를 구할 때 쓴다. 오차 ±1° 수준이면 그림자 길이 용도로 충분하다.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime


def sun_altitude_azimuth(
    latitude_deg: float, longitude_deg: float, dt_utc: datetime
) -> tuple[float, float]:
    """UTC 시각의 태양 (고도°, 방위각° 북=0 시계방향)을 반환한다."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=UTC)
    dt_utc = dt_utc.astimezone(UTC)

    # 율리우스일 기반 경과 세기
    y, m, d = dt_utc.year, dt_utc.month, dt_utc.day
    hours = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5 + hours / 24
    t = (jd - 2451545.0) / 36525.0

    # 태양 기하 평균 경도·근점이각 → 황경
    l0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360
    m_anom = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    m_rad = math.radians(m_anom)
    c = (
        (1.914602 - t * (0.004817 + 0.000014 * t)) * math.sin(m_rad)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m_rad)
        + 0.000289 * math.sin(3 * m_rad)
    )
    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    # 적위
    e0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    e_corr = e0 + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(
        math.asin(math.sin(math.radians(e_corr)) * math.sin(math.radians(app_long)))
    )

    # 균시차(분) → 진태양시 → 시각각
    var_y = math.tan(math.radians(e_corr / 2)) ** 2
    l0_rad = math.radians(l0)
    eot = 4 * math.degrees(
        var_y * math.sin(2 * l0_rad)
        - 2 * 0.016708634 * math.sin(m_rad)
        + 4 * 0.016708634 * var_y * math.sin(m_rad) * math.cos(2 * l0_rad)
        - 0.5 * var_y * var_y * math.sin(4 * l0_rad)
        - 1.25 * 0.016708634**2 * math.sin(2 * m_rad)
    )
    true_solar_min = (hours * 60 + eot + 4 * longitude_deg) % 1440
    hour_angle = true_solar_min / 4 - 180 if true_solar_min / 4 >= 0 else true_solar_min / 4 + 180

    # 고도·방위각
    lat_rad = math.radians(latitude_deg)
    decl_rad = math.radians(decl)
    ha_rad = math.radians(hour_angle)
    zenith = math.acos(
        math.sin(lat_rad) * math.sin(decl_rad)
        + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad)
    )
    altitude = 90.0 - math.degrees(zenith)

    az_cos = (math.sin(lat_rad) * math.cos(zenith) - math.sin(decl_rad)) / (
        math.cos(lat_rad) * math.sin(zenith)
    )
    az_cos = max(-1.0, min(1.0, az_cos))
    azimuth = math.degrees(math.acos(az_cos))
    if hour_angle > 0:
        azimuth = (azimuth + 180) % 360
    else:
        azimuth = (540 - azimuth) % 360
    return altitude, azimuth
