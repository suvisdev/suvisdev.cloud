"""ShowtimePort 구현 — 롯데시네마 내부 JSON 엔드포인트(Phase 2).

robots.txt 전체 허용(2026-08-28·08-31 실확인). 설계서 §5 완화책 준수:
질의 시점 단건 조회만(대량 선수집 금지), 단기 캐시, 저빈도 호출,
실패 시 None(Phase 1 딥링크 폴백).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from mova.app.dtos.market_chat_dto import CinemaShowtimeDto, ShowtimeSlotDto
from mova.app.ports.output.showtime_port import ShowtimePort

logger = logging.getLogger(__name__)

_BASE = "https://www.lottecinema.co.kr/LCWS"
_CINEMA_PATH = "/Cinema/CinemaData.aspx"
_TICKET_PATH = "/Ticketing/TicketingData.aspx"
_TIMEOUT_S = 10.0
_CINEMA_CACHE_TTL_S = 86_400  # 24시간


@dataclass(frozen=True)
class _LotteCinema:
    cinema_id: int
    division_code: int
    detail_division_code: str
    name: str


def _normalize(s: str) -> str:
    return "".join(s.split()).lower()


class LotteCinemaAdapter(ShowtimePort):
    def __init__(self) -> None:
        self._cinemas: list[_LotteCinema] = []
        self._cinemas_fetched_at: float = 0.0

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

        if date is None:
            from datetime import UTC, datetime, timedelta

            date = (datetime.now(UTC) + timedelta(hours=9)).strftime("%Y-%m-%d")

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

        items = (data.get("PlaySeqs") or {}).get("Items") or []
        wanted = _normalize(movie_title)
        slots: list[ShowtimeSlotDto] = []
        for item in items:
            name_kr = item.get("MovieNameKR") or ""
            if wanted not in _normalize(name_kr) and _normalize(name_kr) not in wanted:
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
                )
            )

        if not slots:
            return None

        slots.sort(key=lambda s: s.start_time)
        return CinemaShowtimeDto(cinema_name=f"롯데시네마 {cinema.name}", slots=slots)

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
        stripped_norm = _normalize(stripped)
        if not stripped_norm:
            return None

        for c in self._cinemas:
            c_norm = _normalize(c.name)
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
                )
            )
        self._cinemas = cinemas
        self._cinemas_fetched_at = time.monotonic()
        logger.info("[LotteCinemaAdapter] 극장 목록 캐시 갱신: %d곳", len(cinemas))


def _to_json(d: dict) -> str:
    import json

    return json.dumps(d, ensure_ascii=False)
