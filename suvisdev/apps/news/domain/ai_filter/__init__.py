"""AI 뉴스 규칙 판정기 — newsdesk 하네스(news-ai-filter)와 같은 코드. 표준 라이브러리만 쓴다."""

from .classifier import badge_of, classify, decide, load_sources, load_thresholds

__all__ = ["badge_of", "classify", "decide", "load_sources", "load_thresholds"]
