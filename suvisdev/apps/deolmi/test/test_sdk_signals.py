"""SDK가 실제로 만드는 신호로 서버 판정을 본다 — 손으로 지은 신호 dict가 아니라.

브라우저가 시나리오마다 내는 이벤트 순서(HTML 명세 기준)를 node에서 SDK 리스너에 그대로 흘려
features()를 뽑고(sdk_driver.js), 그 값을 SignalsSchema → 인터랙터(모델은 0.99를 내는 fake)에 넣는다.
node가 없으면 건너뛴다(운영 이미지에는 없고, 로컬·GitHub ubuntu 러너에는 있다).
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest
from fakes import (
    _FakeEventRepository,
    _FakeModel,
    _FakeRedis,
    _FakeSiteRepository,
    _FakeVelocity,
    make_site,
)

from deolmi.adapter.inbound.api.schemas.score_schema import SignalsSchema
from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.dtos.score_dto import ScoreCommand
from deolmi.app.use_cases.score_interactor import ScoreInteractor
from deolmi.domain.services.scoring_policy import no_mouse_input

_HERE = Path(__file__).parent
_SDK = _HERE.parent / "sdk" / "deolmi.js"
_END_MS = 8000

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 필요")


def _sdk_features(events: list[dict]) -> dict:
    out = subprocess.run(
        ["node", str(_HERE / "sdk_driver.js"), str(_SDK), json.dumps(events), str(_END_MS)],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return json.loads(out.stdout)


def _typing(start: int, n: int, *, jitter: bool = True) -> list[dict]:
    rng = random.Random(7)
    t, evs = start, []
    for _ in range(n):
        t += rng.randint(80, 320) if jitter else 10
        evs.append({"t": t, "type": "keydown"})
    return evs


def _trusted_click(t: int, *, detail: int, pointer_type: str) -> dict:
    return {
        "t": t,
        "type": "click",
        "isTrusted": True,
        "detail": detail,
        "pointerType": pointer_type,
    }


# 제출 버튼 없는 폼에서 Enter: 명세상 click 없이 바로 submit — 키 입력만 남는다.
IMPLICIT_SUBMIT = _typing(1500, 12)
# 버튼에 포커스하고 Enter/Space: 브라우저가 detail 0인 진짜 클릭을 만든다.
KEYBOARD_BUTTON = [*_typing(1500, 12), _trusted_click(6000, detail=0, pointer_type="")]
# 휴대폰: 스크롤(touchstart/move), 탭(touch pointermove는 SDK가 무시, 호환 mousemove엔 리스너 없음), 클릭은 detail 1.
TOUCH = [
    {"t": 500, "type": "touchstart"},
    *[{"t": 520 + i * 16, "type": "touchmove"} for i in range(10)],
    {"t": 900, "type": "pointermove", "pointerType": "touch", "clientX": 10, "clientY": 10},
    {"t": 905, "type": "mousemove", "clientX": 200, "clientY": 600},
    *_typing(1500, 12),
    {"t": 6900, "type": "touchstart"},
    _trusted_click(7000, detail=1, pointer_type="touch"),
]
# 스크립트의 el.click(): isTrusted false, 움직임·키·터치 없음.
SCRIPT_CLICK = [{"t": 50, "type": "click", "isTrusted": False, "detail": 0, "pointerType": ""}]
# Enter 제출을 흉내 낸 자동 입력: 클릭 없이 키만, 간격이 일정.
SCRIPTED_TYPING = _typing(100, 12, jitter=False)


async def _verdict(signals: dict) -> tuple[str, float | None]:
    it = ScoreInteractor(
        sites=_FakeSiteRepository(make_site()),
        events=_FakeEventRepository(),
        model=_FakeModel(0.99),  # 마우스 세션만 아는 모델이 마우스 없는 세션에 내던 값(실측 0.99)
        tokens=JwtScoreTokenAdapter("s", _FakeRedis()),
        velocity=_FakeVelocity(),
    )
    issued = await it.score(ScoreCommand("pk_test", signals, None, "1.2.3.4"))
    return issued.verdict, issued.event.result.model_score


def _validated(events: list[dict]) -> dict:
    return SignalsSchema.model_validate(_sdk_features(events)).model_dump()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("events", "kbd_clicks", "touches"),
    [(IMPLICIT_SUBMIT, 0, 0), (KEYBOARD_BUTTON, 1, 0), (TOUCH, 0, 12)],
    ids=["enter-implicit-submit", "enter-on-button", "touch"],
)
async def test_keyboard_and_touch_humans_from_real_sdk_are_allowed(events, kbd_clicks, touches):
    s = _validated(events)
    # 터치 좌표·호환 mousemove는 궤적에 안 들어간다
    assert s["move_count"] == 0 and s["path_px"] == 0
    assert s["kbd_click_count"] == kbd_clicks and s["touch_count"] == touches
    assert no_mouse_input(s)
    assert await _verdict(s) == ("allow", None)  # 모델(0.99)을 건너뛴다


@pytest.mark.asyncio
async def test_script_click_from_real_sdk_is_still_blocked():
    s = _validated(SCRIPT_CLICK)
    assert s["click_count"] == 1 and s["kbd_click_count"] == 0  # isTrusted false는 키보드 클릭 아님
    assert not no_mouse_input(s)
    assert (await _verdict(s))[0] == "block"


@pytest.mark.asyncio
async def test_scripted_typing_without_clicks_still_hits_key_rhythm_rule():
    # 키만 있는 세션은 모델을 건너뛰지만 키 리듬 규칙은 그대로 — 일정 간격 자동 입력은 차단.
    s = _validated(SCRIPTED_TYPING)
    assert no_mouse_input(s)
    assert await _verdict(s) == ("block", None)
