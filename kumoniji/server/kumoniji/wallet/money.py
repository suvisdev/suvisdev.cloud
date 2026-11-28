"""화폐 숫자와 순수 계산(DB 없음). 숫자를 바꿀 땐 이 파일만 — 근거는 계획 D 'Claude가 정한 기본값'·ADR-0024."""

POINT = 50  # 1점 = 판돈 50(11-24 사용자)
MIN_STAKE = 500  # 자동 매칭 입장 최소 판돈
HEART_MAX, HEART_EVERY = 10, 600
ATTEND, ATTEND_7TH, ATTEND_7TH_GEMS = 200, 500, 10
MISSION, MISSION_BONUS, MISSION_NEED = 100, 300, 5
# 광고 보상(11-28 사용자 '상점에 광고 모드 만들어 두기'): 한 편에 햇살 1, 하루 5번
AD_HEARTS, AD_PER_DAY = 1, 5
# 상품: (무지개 조각 값, 얻는 것). 많이 살수록 덤(보통 게임 상점처럼, 11-27 사용자) — 골드 1,000·5,500(+10%)·
# 12,000(+20%)·40,000(+33%), 햇살 5·15(+20%). 옛 id(hearts5·coins1000)는 원장 참조에 남아 있어 그대로 둔다
SHOP = {
    "coins1000": (10, {"coins": 1000}),
    "coins5500": (50, {"coins": 5500}),
    "coins12000": (100, {"coins": 12000}),
    "coins40000": (300, {"coins": 40000}),
    "hearts5": (10, {"hearts": 5}),
    "hearts15": (25, {"hearts": 15}),
}


def regen(hearts: int, since: float, now: float) -> tuple[int, float]:
    """10분에 1개, 10개까지. 10 이상(산 하트 포함)이면 충전 없이 기준 시각을 지금으로(뒤로는 안 감 — 늦게 잠근 옛 요청)."""
    if hearts >= HEART_MAX:
        return hearts, max(since, now)
    got = max(int((now - since) // HEART_EVERY), 0)  # 동시 요청으로 now가 기준 시각보다 앞설 수 있다
    if hearts + got >= HEART_MAX:
        return HEART_MAX, now
    return hearts + got, since + got * HEART_EVERY


def stake(points: list[int], balances: list[int]) -> list[int]:
    """판돈 증감. 진 사람은 점수×50을 내되 잔고까지만, 이긴 사람은 실제로 걷힌 돈을 + 점수 비율로 나눈다(합 0)."""
    paid = [min(-p * POINT, b) if p < 0 else 0 for p, b in zip(points, balances)]
    pot = sum(paid)
    plus = [max(p, 0) for p in points]
    total = sum(plus) or 1
    got = [pot * p // total for p in plus]
    if pot and any(plus):
        got[max(range(len(plus)), key=lambda i: plus[i])] += pot - sum(got)  # 나머지는 가장 많이 받는 사람에게
    return [g - p for g, p in zip(got, paid)]
