"""ShowtimePort 구현 — 롯데시네마 내부 JSON 엔드포인트(Phase 2).

robots.txt 전체 허용(2026-08-28·08-31 실확인). 설계서 §5 완화책 준수:
질의 시점 단건 조회만(대량 선수집 금지), 단기 캐시, 저빈도 호출,
실패 시 None(Phase 1 딥링크 폴백).
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass
from typing import Any

import httpx

from mova.app.dtos.market_chat_dto import CinemaShowtimeDto, ShowtimeSlotDto
from mova.app.ports.output.showtime_port import ShowtimePort
from mova.domain.value_objects.movie_title import MovieTitle, normalize_title

logger = logging.getLogger(__name__)

_BASE = "https://www.lottecinema.co.kr/LCWS"
_CINEMA_PATH = "/Cinema/CinemaData.aspx"
_TICKET_PATH = "/Ticketing/TicketingData.aspx"
_TIMEOUT_S = 10.0
_CINEMA_CACHE_TTL_S = 86_400  # 24시간
_PLAY_CACHE_TTL_S = 600  # 극장·날짜별 회차 캐시 — 광역 조회가 극장 수만큼 호출하므로
_PARALLEL = 6
# 롯데 극장 목록의 지역 그룹(DivisionCode=1의 DetailDivisionCode) — 2026-09-28 극장 이름으로 실측.
_AREA_DETAIL_CODE = {
    "서울": "0001",
    "경기": "0002",
    "인천": "0002",
    "대전": "0003",
    "세종": "0003",
    "충북": "0003",
    "충남": "0003",
    "충청": "0003",
    "광주": "0004",
    "전북": "0004",
    "전남": "0004",
    "전라": "0004",
    "대구": "0005",
    "부산": "0005",
    "울산": "0005",
    "경북": "0005",
    "경남": "0005",
    "경상": "0005",
    "강원": "0006",
    "제주": "0007",
}
_WEB = "https://www.lottecinema.co.kr/NLCHS"


def booking_url(
    *, cinema_id: int, movie_code: str, play_date: str, start_time: str, screen_id: str
) -> str:
    """예매 화면 딥링크. 롯데 웹 `TicketingIndex.bundle.js`가 `link_channelCode=naver`일 때만
    `link_cinemaCode`(CinemaID)·`link_movieCd`·`link_date`를 선택 상태로 넣고, `link_time`+
    `link_screenId`와 일치하는 회차를 강조한다(2026-09-28 번들 실측)."""
    return (
        f"{_WEB}/Ticketing?link_channelCode=naver&link_cinemaCode={cinema_id}"
        f"&link_movieCd={movie_code}&link_date={play_date}"
        f"&link_time={start_time}&link_screenId={screen_id}"
    )


def timetable_url(*, division_code: int, detail_division_code: str, cinema_id: int) -> str:
    """극장 상세(시간표) 페이지 — 사이트 링크 형식은 detailDivisionCode를 정수로 쓴다("0001"→1)."""
    return (
        f"{_WEB}/Cinema/Detail?divisionCode={division_code}"
        f"&detailDivisionCode={int(detail_division_code or 1)}&cinemaID={cinema_id}"
    )


@dataclass(frozen=True)
class _LotteCinema:
    cinema_id: int
    division_code: int
    detail_division_code: str
    name: str
    lat: float = 0.0
    lng: float = 0.0


class LotteCinemaAdapter(ShowtimePort):
    def __init__(self) -> None:
        self._cinemas: list[_LotteCinema] = []
        self._cinemas_fetched_at: float = 0.0
        self._play_cache: dict[tuple[int, str], tuple[float, list[dict[str, Any]]]] = {}

    async def fetch_showtimes(
        self, cinema_name: str, movie_title: str, *, date: str | None = None
    ) -> CinemaShowtimeDto | None:
        cinema_name = (cinema_name or "").strip()
        movie_title = (movie_title or "").strip()
        if not cinema_name or not movie_title:
            return None

        cinema = await self._match_cinema(cinema_name)
        if cinema is None:
            return None

        date = date or _kst_today()
        items = await self._play_items(cinema, date)
        if items is None:
            return None
        return self._to_showtime(cinema, items, movie_title, date)

    async def find_showing_cinemas(
        self, area: str, movie_title: str, *, date: str | None = None
    ) -> list[CinemaShowtimeDto]:
        code = _AREA_DETAIL_CODE.get((area or "").strip())
        if not code or not (movie_title or "").strip():
            return []
        await self._ensure_cinemas()
        seen: set[int] = set()
        targets: list[_LotteCinema] = []
        for c in self._cinemas:
            # DivisionCode=2는 특별관 묶음(같은 극장 중복) — 지역 그룹만, 극장당 한 번.
            if c.division_code == 1 and c.detail_division_code == code and c.cinema_id not in seen:
                seen.add(c.cinema_id)
                targets.append(c)
        results = await self._scan(targets, movie_title, date or _kst_today())
        logger.info(
            "[LotteCinemaAdapter] 광역 조회 area=%s cinemas=%d showing=%d date=%s",
            area,
            len(targets),
            len(results),
            date,
        )
        return results

    async def find_showing_cinemas_near(
        self,
        lat: float,
        lng: float,
        movie_title: str,
        *,
        date: str | None = None,
        max_km: float = 5.0,
    ) -> list[CinemaShowtimeDto]:
        if not (movie_title or "").strip():
            return []
        await self._ensure_cinemas()
        seen: set[int] = set()
        targets: list[_LotteCinema] = []
        for c in self._cinemas:
            if c.cinema_id in seen or (c.lat == 0.0 and c.lng == 0.0):
                continue
            if _haversine_km(lat, lng, c.lat, c.lng) <= max_km:
                seen.add(c.cinema_id)
                targets.append(c)
        results = await self._scan(targets, movie_title, date or _kst_today())
        logger.info(
            "[LotteCinemaAdapter] 반경 조회 %.4f,%.4f %.1fkm cinemas=%d showing=%d",
            lat,
            lng,
            max_km,
            len(targets),
            len(results),
        )
        return results

    async def _scan(
        self, targets: list[_LotteCinema], movie_title: str, date: str
    ) -> list[CinemaShowtimeDto]:
        """극장들의 회차를 병렬(동시 6)로 받아 이 작품 상영관만, 첫 회차 순으로."""
        sem = asyncio.Semaphore(_PARALLEL)

        async def one(c: _LotteCinema) -> CinemaShowtimeDto | None:
            async with sem:
                items = await self._play_items(c, date)
            return self._to_showtime(c, items, movie_title, date) if items else None

        results = [r for r in await asyncio.gather(*(one(c) for c in targets)) if r is not None]
        results.sort(key=lambda cs: cs.slots[0].start_time)
        return results

    async def _play_items(self, cinema: _LotteCinema, date: str) -> list[dict[str, Any]] | None:
        """극장 하루 회차 원본(모든 작품). 10분 캐시. 실패는 None."""
        key = (cinema.cinema_id, date)
        hit = self._play_cache.get(key)
        if hit and time.monotonic() - hit[0] < _PLAY_CACHE_TTL_S:
            return hit[1]
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                cinema_id_param = (
                    f"{cinema.division_code}|{cinema.detail_division_code}|{cinema.cinema_id}"
                )
                payload = {
                    "MethodName": "GetPlaySequence",
                    "channelType": "HO",
                    "osType": "W",
                    "osVersion": "Mozilla/5.0",
                    "playDate": date,
                    "cinemaID": cinema_id_param,
                    "representationMovieCode": "",
                }
                res = await client.post(
                    f"{_BASE}{_TICKET_PATH}",
                    data={"paramList": _to_json(payload)},
                )
                res.raise_for_status()
                data = res.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("[LotteCinemaAdapter] 시간표 조회 실패 cinema=%s | %s", cinema.name, e)
            return None
        if data.get("IsOK") not in ("true", True):
            logger.info("[LotteCinemaAdapter] IsOK=false cinema=%s", cinema.name)
            return None
        items = list((data.get("PlaySeqs") or {}).get("Items") or [])
        self._play_cache[key] = (time.monotonic(), items)
        return items

    @staticmethod
    def _to_showtime(
        cinema: _LotteCinema, items: list[dict[str, Any]], movie_title: str, date: str
    ) -> CinemaShowtimeDto | None:
        wanted = MovieTitle(movie_title)
        slots: list[ShowtimeSlotDto] = []
        for item in items:
            name_kr = item.get("MovieNameKR") or ""
            if not wanted.overlaps(name_kr):
                continue
            total = int(item.get("TotalSeatCount") or 0)
            booked = int(item.get("BookingSeatCount") or 0)
            slots.append(
                ShowtimeSlotDto(
                    screen=str(item.get("ScreenNameKR") or ""),
                    start_time=str(item.get("StartTime") or ""),
                    end_time=str(item.get("EndTime") or ""),
                    film_type=str(item.get("FilmNameKR") or ""),
                    seats_available=max(total - booked, 0),
                    seats_total=total,
                    booking_url=booking_url(
                        cinema_id=cinema.cinema_id,
                        movie_code=str(
                            item.get("RepresentationMovieCode") or item.get("MovieCode") or ""
                        ),
                        play_date=str(item.get("PlayDt") or date),
                        start_time=str(item.get("StartTime") or ""),
                        screen_id=str(item.get("ScreenID") or ""),
                    ),
                )
            )
        if not slots:
            return None
        slots.sort(key=lambda s: s.start_time)
        return CinemaShowtimeDto(
            cinema_name=f"롯데시네마 {cinema.name}",
            slots=slots,
            timetable_url=timetable_url(
                division_code=cinema.division_code,
                detail_division_code=cinema.detail_division_code,
                cinema_id=cinema.cinema_id,
            ),
        )

    async def fetch_nearest_showtimes(
        self,
        lat: float,
        lng: float,
        movie_title: str,
        *,
        date: str | None = None,
        max_km: float = 10.0,
    ) -> CinemaShowtimeDto | None:
        cinema = await self._find_nearest_cinema(lat, lng, max_km=max_km)
        if cinema is None:
            return None
        fake_name = f"롯데시네마 {cinema.name}"
        return await self.fetch_showtimes(fake_name, movie_title, date=date)

    async def _find_nearest_cinema(
        self, lat: float, lng: float, *, max_km: float = 10.0
    ) -> _LotteCinema | None:
        await self._ensure_cinemas()
        best: _LotteCinema | None = None
        best_dist = float("inf")
        for c in self._cinemas:
            if c.lat == 0.0 and c.lng == 0.0:
                continue
            d = _haversine_km(lat, lng, c.lat, c.lng)
            if d < best_dist:
                best_dist = d
                best = c
        if best is not None and best_dist <= max_km:
            logger.info("[LotteCinemaAdapter] 최근접 극장=%s dist=%.1fkm", best.name, best_dist)
            return best
        return None

    async def _match_cinema(self, kakao_name: str) -> _LotteCinema | None:
        """카카오 place_name → 롯데시네마 매칭. "롯데시네마" 접두사를 떼고 비교."""
        if "롯데" not in kakao_name:
            return None

        await self._ensure_cinemas()
        if not self._cinemas:
            return None

        stripped = kakao_name
        for prefix in ("롯데시네마 ", "롯데시네마"):
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix) :]
                break
        stripped_norm = normalize_title(stripped)  # 극장명도 같은 키 규칙(공백 제거+소문자)
        if not stripped_norm:
            return None

        for c in self._cinemas:
            c_norm = normalize_title(c.name)
            if c_norm == stripped_norm or c_norm in stripped_norm or stripped_norm in c_norm:
                return c
        return None

    async def _ensure_cinemas(self) -> None:
        if self._cinemas and (time.monotonic() - self._cinemas_fetched_at) < _CINEMA_CACHE_TTL_S:
            return
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                payload = {
                    "MethodName": "GetCinemaItems",
                    "channelType": "HO",
                    "osType": "W",
                    "osVersion": "Mozilla/5.0",
                    "divisionCode": "",
                    "detailDivisionCode": "",
                    "memberOnNo": "0",
                }
                res = await client.post(
                    f"{_BASE}{_CINEMA_PATH}",
                    data={"paramList": _to_json(payload)},
                )
                res.raise_for_status()
                data = res.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("[LotteCinemaAdapter] 극장 목록 조회 실패 | %s", e)
            return

        raw_items = (data.get("Cinemas") or {}).get("Items") or []
        cinemas = []
        for item in raw_items:
            cid = item.get("CinemaID")
            name = item.get("CinemaNameKR") or item.get("CinemaName")
            if cid is None or not name:
                continue
            cinemas.append(
                _LotteCinema(
                    cinema_id=int(cid),
                    division_code=int(item.get("DivisionCode") or 1),
                    detail_division_code=str(item.get("DetailDivisionCode") or "0001"),
                    name=str(name),
                    lat=float(item.get("Latitude") or 0),
                    lng=float(item.get("Longitude") or 0),
                )
            )
        self._cinemas = cinemas
        self._cinemas_fetched_at = time.monotonic()
        logger.info("[LotteCinemaAdapter] 극장 목록 캐시 갱신: %d곳", len(cinemas))


def _kst_today() -> str:
    from datetime import UTC, datetime, timedelta

    return (datetime.now(UTC) + timedelta(hours=9)).strftime("%Y-%m-%d")


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _to_json(d: dict[str, Any]) -> str:
    import json

    return json.dumps(d, ensure_ascii=False)
