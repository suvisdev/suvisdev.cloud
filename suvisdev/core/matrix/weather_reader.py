"""OpenWeatherMap 현재 날씨·예보 조회."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

import httpx

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

_WEEKDAY_KO = ("월", "화", "수", "목", "금", "토", "일")


class WeatherReaderError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


async def fetch_current_weather(*, city: str, api_key: str) -> dict[str, str | float]:
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "kr",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OWM_CURRENT_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise _owm_request_error(e) from e
    except httpx.RequestError as e:
        raise WeatherReaderError(f"OpenWeatherMap 연결 실패: {e!s}") from e

    main = data.get("main") or {}
    weather_list = data.get("weather") or []
    if not weather_list:
        raise WeatherReaderError("날씨 데이터가 비어 있습니다.")

    w0 = weather_list[0]
    temp = main.get("temp")
    if temp is None:
        raise WeatherReaderError("온도 정보를 찾을 수 없습니다.")

    return {
        "city": str(data.get("name") or city),
        "temp_c": round(float(temp), 1),
        "description": str(w0.get("description") or ""),
        "icon": str(w0.get("icon") or "01d"),
    }


def _owm_request_error(e: httpx.HTTPStatusError) -> WeatherReaderError:
    detail = ""
    try:
        body = e.response.json()
        detail = body.get("message", "")
    except Exception:
        detail = e.response.text[:200]
    code = e.response.status_code
    return WeatherReaderError(
        detail or f"OpenWeatherMap HTTP {code}",
        status_code=401 if code == 401 else 502,
    )


async def fetch_weekly_forecast(*, city: str, api_key: str) -> dict[str, object]:
    """5일/3시간 예보 API를 일별로 묶어 최대 7일치를 반환한다 (무료 플랜은 보통 5일)."""
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "kr",
        "cnt": 40,
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(OWM_FORECAST_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise _owm_request_error(e) from e
    except httpx.RequestError as e:
        raise WeatherReaderError(f"OpenWeatherMap 연결 실패: {e!s}") from e

    items = data.get("list") or []
    if not items:
        raise WeatherReaderError("예보 데이터가 비어 있습니다.")

    by_day: dict[str, dict[str, list]] = defaultdict(
        lambda: {"temps": [], "icons": [], "descs": [], "hours": []}
    )
    for item in items:
        dt = datetime.fromtimestamp(int(item["dt"]), tz=UTC)
        day_key = dt.strftime("%Y-%m-%d")
        main = item.get("main") or {}
        w0 = (item.get("weather") or [{}])[0]
        by_day[day_key]["temps"].append(float(main.get("temp", 0)))
        by_day[day_key]["icons"].append(str(w0.get("icon") or "01d"))
        by_day[day_key]["descs"].append(str(w0.get("description") or ""))
        by_day[day_key]["hours"].append(dt.hour)

    days: list[dict[str, str | float]] = []
    for day_key in sorted(by_day.keys())[:5]:
        bucket = by_day[day_key]
        temps = bucket["temps"]
        icons: list[str] = bucket["icons"]
        descs: list[str] = bucket["descs"]
        hours: list[int] = bucket["hours"]

        noon_idx = min(range(len(hours)), key=lambda i: abs(hours[i] - 12))
        desc = descs[noon_idx] if descs else ""
        icon = icons[noon_idx] if icons else "01d"

        dt = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=UTC)
        weekday = _WEEKDAY_KO[dt.weekday()]

        days.append(
            {
                "date": day_key,
                "weekday": weekday,
                "temp_min": round(min(temps), 1),
                "temp_max": round(max(temps), 1),
                "description": desc,
                "icon": icon,
            }
        )

    return {
        "city": str((data.get("city") or {}).get("name") or city),
        "days": days,
    }
