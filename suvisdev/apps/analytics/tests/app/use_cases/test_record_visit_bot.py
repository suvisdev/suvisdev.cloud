"""User-Agent 봇 판정과 통계 분리(2026-09-29) — 사람·봇·1회성."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from analytics.app.use_cases.get_visitor_summary_interactor import GetVisitorSummaryInteractor
from analytics.app.use_cases.record_visit_interactor import (
    RecordVisitInteractor,
    is_bot_user_agent,
)
from analytics.tests.app.fakes import _FakeVisitorActivityRepository

_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
_GOOGLE = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
_KAKAO = "facebookexternalhit/1.1; kakaotalk-scrap/1.0; +https://devtalk.kakao.com/t/scrap/33984"


def test_bot_user_agent_rule():
    assert not is_bot_user_agent(_CHROME)
    assert is_bot_user_agent(_GOOGLE)
    assert is_bot_user_agent(_KAKAO)
    assert is_bot_user_agent("curl/8.5.0")
    assert is_bot_user_agent(None) and is_bot_user_agent("")  # 브라우저는 항상 UA를 보낸다


@pytest.mark.asyncio
async def test_summary_separates_humans_bots_and_one_shot():
    repo = _FakeVisitorActivityRepository()
    record = RecordVisitInteractor(repository=repo)
    human = "11111111-1111-4111-8111-111111111111"
    stayer = "22222222-2222-4222-8222-222222222222"
    bot = "33333333-3333-4333-8333-333333333333"
    await record.record(human, _CHROME)  # 핑 1회 → 1회성
    await record.record(stayer, _CHROME)
    await record.record(stayer, _CHROME)  # 두 번째 핑 → 체류
    await record.record(bot, _GOOGLE)
    key = next(k for k in repo.rows if k[0] == stayer)
    repo.rows[key] = (repo.rows[key][0], datetime.now(UTC))  # last_seen 갱신

    dto = await GetVisitorSummaryInteractor(repository=repo).summary()
    assert (dto.today, dto.today_bots, dto.today_one_shot) == (2, 1, 1)
    assert dto.cumulative_total == 2  # 봇은 누적에서도 제외
    assert dto.last_7_days_series[-1].bots == 1 and dto.last_7_days_series[-1].one_shot == 1
    assert repo.agents[next(k for k in repo.rows if k[0] == bot)] == _GOOGLE
