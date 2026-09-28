"""롯데시네마 딥링크 생성 — 예매 화면(회차 강조)·극장 시간표 페이지 URL(2026-09-28)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
for _p in (_ROOT, _ROOT / "apps"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from mova.adapter.outbound.http.lotte_cinema_adapter import (  # noqa: E402
    booking_url,
    timetable_url,
)


class LotteLinkTests(unittest.TestCase):
    def test_booking_url_carries_naver_link_params(self) -> None:
        """롯데 웹 번들은 link_channelCode=naver일 때만 link_* 값을 선택 상태로 반영한다."""
        url = booking_url(
            cinema_id=1004,
            movie_code="24623",
            play_date="2026-09-28",
            start_time="12:40",
            screen_id="301",
        )
        self.assertTrue(url.startswith("https://www.lottecinema.co.kr/NLCHS/Ticketing?"))
        for part in (
            "link_channelCode=naver",
            "link_cinemaCode=1004",
            "link_movieCd=24623",
            "link_date=2026-09-28",
            "link_time=12:40",
            "link_screenId=301",
        ):
            self.assertIn(part, url)

    def test_timetable_url_uses_integer_detail_division(self) -> None:
        url = timetable_url(division_code=1, detail_division_code="0001", cinema_id=1004)
        self.assertEqual(
            url,
            "https://www.lottecinema.co.kr/NLCHS/Cinema/Detail"
            "?divisionCode=1&detailDivisionCode=1&cinemaID=1004",
        )


class LotteAreaScanTests(unittest.IsolatedAsyncioTestCase):
    async def test_scans_only_area_group_once_per_cinema_sorted_by_first_slot(self) -> None:
        import time

        from mova.adapter.outbound.http.lotte_cinema_adapter import LotteCinemaAdapter, _LotteCinema

        adapter = LotteCinemaAdapter()
        adapter._cinemas = [
            _LotteCinema(1004, 1, "0001", "건대입구"),
            _LotteCinema(1016, 1, "0001", "월드타워"),
            _LotteCinema(1004, 2, "0986", "건대입구"),  # 특별관 묶음 중복 — 제외
            _LotteCinema(3001, 1, "0002", "광교"),  # 경기 — 제외
        ]
        adapter._cinemas_fetched_at = time.monotonic()
        calls: list[int] = []

        async def fake_items(cinema: _LotteCinema, date: str) -> list[dict]:
            calls.append(cinema.cinema_id)
            start = {1004: "15:00", 1016: "11:00"}[cinema.cinema_id]
            return [{"MovieNameKR": "옵세션", "StartTime": start, "ScreenID": 1}]

        adapter._play_items = fake_items  # type: ignore[method-assign]
        result = await adapter.find_showing_cinemas("서울", "옵세션", date="2026-09-28")

        self.assertEqual(sorted(calls), [1004, 1016])
        self.assertEqual(
            [c.cinema_name for c in result], ["롯데시네마 월드타워", "롯데시네마 건대입구"]
        )
        self.assertEqual(await adapter.find_showing_cinemas("화성", "옵세션"), [])


if __name__ == "__main__":
    unittest.main()
