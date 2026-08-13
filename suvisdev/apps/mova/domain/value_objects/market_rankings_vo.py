"""HOT 랭킹 출처 — MOVA_ERD `rankings.source`."""

RANKING_SOURCE_CHAT_TREND = "chat_trend"
RANKING_SOURCE_BOX_OFFICE = "box_office"
RANKING_SOURCE_MANUAL = "manual"

RANKING_SOURCES = frozenset(
    {
        RANKING_SOURCE_CHAT_TREND,
        RANKING_SOURCE_BOX_OFFICE,
        RANKING_SOURCE_MANUAL,
    },
)

DEFAULT_HOT_RANKING_SOURCE = RANKING_SOURCE_CHAT_TREND

# chat_trend 집계 기본값 — 최근 N일 윈도우, 상위 K건.
DEFAULT_CHAT_TREND_WINDOW_DAYS = 7
DEFAULT_CHAT_TREND_LIMIT = 10


def chat_trend_score(click_count: int) -> int:
    """AI 검색 TOP 점수 — 사용자가 채팅 결과 카드를 실제로 클릭한 횟수.

    2026-08-13: 이전에는 pick_count(=AI가 노출한 횟수)·hit_count(chat 응답 hit)
    가중합이었으나 사용자 지적: "검색만 하고 나오는 걸로 순위 정하는 건 이상,
    클릭했을 때만 반영해야". 노출/추천 신호는 제거, 실제 클릭만 신호로 둔다.
    """
    return click_count
