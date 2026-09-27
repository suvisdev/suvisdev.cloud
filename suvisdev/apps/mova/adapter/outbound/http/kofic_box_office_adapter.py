"""BoxOfficePort 구현 — KOFIC 박스오피스 raw → BoxOfficeEntryDto 매핑."""

from __future__ import annotations

import logging
import time

from mova.adapter.outbound.http.kofic_adapter import KoficAdapter
from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto
from mova.app.ports.output.box_office_port import BoxOfficePort

logger = logging.getLogger(__name__)


def _to_entry(row: dict[str, object]) -> BoxOfficeEntryDto | None:
    title = str(row.get("movieNm") or "").strip()
    rank_raw = str(row.get("rank") or "").strip()
    if not title or not rank_raw.isdigit():
        return None
    open_dt = str(row.get("openDt") or "").strip()
    open_year = int(open_dt[:4]) if len(open_dt) >= 4 and open_dt[:4].isdigit() else None
    return BoxOfficeEntryDto(
        rank=int(rank_raw),
        movie_cd=str(row.get("movieCd") or "").strip(),
        title=title,
        open_year=open_year,
    )


# 주간 박스오피스는 하루 한 번 바뀐다 — 예매 판정·잡담 근거로 요청마다 KOFIC을 부르지 않게
# 1시간 캐시(2026-09-27). 실패는 캐시하지 않는다.
_CACHE_TTL_S = 3600.0
_cache: dict[tuple[str, str], tuple[float, list[BoxOfficeEntryDto]]] = {}


class KoficBoxOfficeAdapter(BoxOfficePort):
    def __init__(self, api_key: str) -> None:
        # 키 검증은 실제 fetch 시점에 KoficAdapter가 수행 (미설정 시 startup 비차단).
        self._api_key = api_key

    async def fetch_box_office(
        self, target_date: str | None, week_gb: str
    ) -> list[BoxOfficeEntryDto]:
        client = KoficAdapter(self._api_key)
        dt = target_date or KoficAdapter.default_target_date()
        cached = _cache.get((dt, week_gb))
        now = time.monotonic()
        if cached is not None and now - cached[0] < _CACHE_TTL_S:
            return cached[1]
        rows = await client.fetch_weekly_boxoffice(dt, week_gb=week_gb)
        entries = [entry for row in rows if (entry := _to_entry(row)) is not None]
        logger.debug("[KoficBoxOfficeAdapter] fetch_box_office dt=%s count=%d", dt, len(entries))
        _cache[(dt, week_gb)] = (now, entries)
        return entries
