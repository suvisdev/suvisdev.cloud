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

# chat_trend 점수 가중치 — pick(추천 노출)을 검색 hit보다 강한 신호로 본다.
# score = pick_count * PICK + hit_sum * HIT
CHAT_TREND_PICK_WEIGHT = 3
CHAT_TREND_HIT_WEIGHT = 1

# chat_trend 집계 기본값 — 최근 N일 윈도우, 상위 K건.
DEFAULT_CHAT_TREND_WINDOW_DAYS = 7
DEFAULT_CHAT_TREND_LIMIT = 10


def chat_trend_score(pick_count: int, hit_sum: int) -> int:
    """pick 횟수와 chat.hit_count 합산의 가중합 점수."""
    return pick_count * CHAT_TREND_PICK_WEIGHT + hit_sum * CHAT_TREND_HIT_WEIGHT
