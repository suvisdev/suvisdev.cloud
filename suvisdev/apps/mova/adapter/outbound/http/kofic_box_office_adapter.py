"""BoxOfficePort 구현 — KOFIC 박스오피스 raw → BoxOfficeEntryDto 매핑."""

from __future__ import annotations

import logging

from mova.adapter.outbound.http.kofic_adapter import KoficAdapter
from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto
from mova.app.ports.output.box_office_port import BoxOfficePort

logger = logging.getLogger(__name__)


def _to_entry(row: dict[str, object]) -> BoxOfficeEntryDto | None:
    title = str(row.get("movieNm") or "").strip()
    rank_raw = str(row.get("rank") or "").strip()
    if not title or not rank_raw.isdigit():
        return None
    return BoxOfficeEntryDto(
        rank=int(rank_raw),
        movie_cd=str(row.get("movieCd") or "").strip(),
        title=title,
    )


class KoficBoxOfficeAdapter(BoxOfficePort):
    def __init__(self, api_key: str) -> None:
        # 키 검증은 실제 fetch 시점에 KoficAdapter가 수행 (미설정 시 startup 비차단).
        self._api_key = api_key

    async def fetch_box_office(
        self, target_date: str | None, week_gb: str
    ) -> list[BoxOfficeEntryDto]:
        client = KoficAdapter(self._api_key)
        dt = target_date or KoficAdapter.default_target_date()
        rows = await client.fetch_weekly_boxoffice(dt, week_gb=week_gb)
        entries = [entry for row in rows if (entry := _to_entry(row)) is not None]
        logger.debug("[KoficBoxOfficeAdapter] fetch_box_office dt=%s count=%d", dt, len(entries))
        return entries
