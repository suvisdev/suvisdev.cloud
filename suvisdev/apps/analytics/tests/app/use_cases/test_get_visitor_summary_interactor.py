from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from analytics.app.use_cases.get_visitor_summary_interactor import GetVisitorSummaryInteractor
from analytics.tests.app.fakes import _FakeVisitorActivityRepository

_KST = ZoneInfo("Asia/Seoul")


def _today_kst() -> date:
    return datetime.now(UTC).astimezone(_KST).date()


class TestGetVisitorSummary:
    @pytest.mark.asyncio
    async def test_aggregates_today_series_and_cumulative(self):
        repository = _FakeVisitorActivityRepository()
        today = _today_kst()
        yesterday = today - timedelta(days=1)
        far_past = today - timedelta(days=30)  # 최근 7일 시리즈에는 안 잡혀야 함
        now = datetime.now(UTC)

        # 오늘 방문자 2명(그 중 1명만 최근 heartbeat로 "지금 접속"에도 잡힘)
        repository.rows[("visitor-a", today)] = (now, now)
        repository.rows[("visitor-b", today)] = (now - timedelta(hours=3), now - timedelta(hours=3))
        # 어제 방문자 1명(오늘과 다른 사람) — last_seen_at도 어제라 "지금 접속"엔 안 잡힘
        repository.rows[("visitor-c", yesterday)] = (
            now - timedelta(days=1),
            now - timedelta(days=1),
        )
        # 30일 전 방문자 1명 — 최근 7일 시리즈/누적에는 포함되지만 오늘/지금 접속엔 안 잡힘
        repository.rows[("visitor-d", far_past)] = (
            now - timedelta(days=30),
            now - timedelta(days=30),
        )

        interactor = GetVisitorSummaryInteractor(repository=repository)
        summary = await interactor.summary()

        assert summary.now_active == 1  # visitor-a만 2분 이내 heartbeat
        assert summary.today == 2  # visitor-a, visitor-b
        assert summary.last_7_days_total == 3  # 오늘 2 + 어제 1 (30일 전은 시리즈 밖)
        assert summary.cumulative_total == 4  # a, b, c, d 전부

    @pytest.mark.asyncio
    async def test_empty_repository_returns_zeros(self):
        repository = _FakeVisitorActivityRepository()
        interactor = GetVisitorSummaryInteractor(repository=repository)

        summary = await interactor.summary()

        assert summary.now_active == 0
        assert summary.today == 0
        assert summary.last_7_days_total == 0
        assert summary.cumulative_total == 0
        assert summary.last_7_days_series == ()
