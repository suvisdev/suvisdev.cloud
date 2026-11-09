"""행동 신호로 '매크로다움'을 점수화하는 규칙 — 외부 의존 없는 도메인 정책.

두 겹 중 1겹(규칙)이다. 사람이 하기 힘든 명백한 신호를 데이터 없이도 바로 잡는다.
2겹(이상 탐지 모델)은 출력 포트 뒤에 있고, 합치는 일은 인터랙터가 한다.
최종 점수는 0~1, 높을수록 매크로 의심. 판정은 구간으로만 나누고 제재는 고객(사람)이 한다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

Verdict = Literal["allow", "challenge", "block"]

BLOCK_THRESHOLD = 0.80
CHALLENGE_THRESHOLD = 0.55

# 같은 사이트·같은 IP가 창(10초) 안에 이만큼 넘게 때리면 의심 — 예매 폭주 대응.
# 속도만으로는 차단하지 않는다(challenge 상한): PC방·회사·통신사 NAT처럼 사람 여럿이 IP 하나를 쓴다.
VELOCITY_SUSPECT = 20
VELOCITY_BURST = 60

# 모델 특징 벡터의 순서. 학습과 추론이 같은 순서여야 한다 — 늘리면 기존 모델 파일은 못 쓴다.
FEATURE_ORDER: tuple[str, ...] = (
    "move_count",  # 마우스·펜 pointermove 이벤트 수(터치는 touch_count로 따로 센다)
    "path_px",  # 마우스 이동 총 거리(px)
    "straightness",  # 시작~끝 직선거리 / 실제 경로 (1에 가까우면 자로 그은 직선)
    "click_iv_mean",  # 클릭 간격 평균(ms)
    "click_iv_std",  # 클릭 간격 표준편차(ms) — 0에 가까우면 기계적
    "key_iv_std",  # 키 입력 간격 표준편차(ms) — 0에 가까우면 붙여넣기/자동 입력
    "dwell_ms",  # 페이지 진입~제출까지 머문 시간(ms)
)


@dataclass(frozen=True)
class RuleResult:
    score: float
    reasons: tuple[str, ...]


def to_features(signals: Mapping[str, float]) -> list[float]:
    return [float(signals.get(k, 0.0)) for k in FEATURE_ORDER]


def no_mouse_input(s: Mapping[str, float]) -> bool:
    """마우스 없이 터치·키보드로 쓴 세션 — 모바일 사용자, Enter로 제출하는 사람.

    모델은 마우스 세션으로만 학습했으므로(마우스 특징이 0이면 무조건 '이상치') 이런 세션은
    모델로 판단하지 않는다(키 리듬 등 규칙은 그대로 본다). 키보드 사용자는 두 경우다 —
    버튼을 Enter로 누르면 키보드 클릭(kbd_click_count)이 남고, 제출 버튼 없는 폼에서 Enter로
    바로 제출(implicit submission)하면 클릭이 아예 없이 키 입력만 남는다.
    단 터치·키보드 흔적이 없는 '움직임 없는 클릭'은 여기 해당하지 않는다.
    """
    if s.get("move_count", 0) != 0:
        return False
    keys_only = s.get("key_count", 0) > 0 and s.get("click_count", 0) == 0
    return s.get("touch_count", 0) > 0 or s.get("kbd_click_count", 0) > 0 or keys_only


def rule_score(s: Mapping[str, float], velocity_count: int) -> RuleResult:
    score, reasons = 0.0, []

    def hit(value: float, reason: str) -> None:
        nonlocal score
        score = max(score, value)
        reasons.append(reason)

    if s.get("key_count", 0) >= 4 and s.get("key_iv_std", 999) < 4:
        hit(0.95, "키 입력 간격이 거의 일정함(자동 입력/붙여넣기 의심)")
    if s.get("click_count", 0) >= 3 and s.get("click_iv_std", 999) < 8:
        hit(0.90, "클릭 간격이 비정상적으로 규칙적")
    if s.get("path_px", 0) > 50 and s.get("straightness", 0) > 0.985:
        hit(0.85, "마우스가 자로 그은 듯 직선으로 이동")
    # 키보드(Enter·Space)가 만든 클릭과 터치는 마우스가 안 움직여도 사람이다 — 그 밖의 클릭만 본다.
    mouse_clicks = s.get("click_count", 0) - s.get("kbd_click_count", 0)
    if mouse_clicks >= 1 and s.get("move_count", 0) == 0 and s.get("touch_count", 0) == 0:
        hit(0.80, "마우스 움직임 없이 클릭만 발생")
    if 0 < s.get("dwell_ms", 1e9) < 300:
        hit(0.75, "폼을 채우고 제출하기까지 시간이 비현실적으로 짧음")

    if velocity_count >= VELOCITY_BURST:
        hit(0.75, "같은 출처에서 비정상적으로 많은 요청(폭주)")
    elif velocity_count >= VELOCITY_SUSPECT:
        hit(0.60, "같은 출처에서 요청이 몰림")

    return RuleResult(score=score, reasons=tuple(reasons))


def verdict_of(score: float) -> Verdict:
    if score >= BLOCK_THRESHOLD:
        return "block"  # 거의 확실 — 그래도 자동 차단보다 추가 확인 권장
    if score >= CHALLENGE_THRESHOLD:
        return "challenge"  # 애매 — 다음 단계(캡차 등)로
    return "allow"
