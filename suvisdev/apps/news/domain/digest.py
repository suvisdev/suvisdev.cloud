"""아침 메일 — 어제(한국 시각) 범위, 고르는 순서, 본문 만들기. 외부 의존 없음.

글이 기술 소식인지와 학습 가치는 모델이 정하고(adapter/outbound/llm/ollama_article_classifier.py),
여기서는 그 결과를 학습 가치·화제 수치·출처 순으로 줄 세운다.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from html import escape

KST = timezone(timedelta(hours=9))
SEND_HOUR_KST = 7
MAX_ITEMS = 10
MAX_PER_GROUP = 4  # 커뮤니티 글이 많아도 메일을 다 차지하지 않게
# 같은 학습 가치면 1차 출처를 앞에 둔다. 논문은 하루 수백 건이라 화제 수치가 있는 것만 후보다(저장소 쿼리).
_GROUP_ORDER = ("lab", "release", "paper", "commentary", "ko_media", "community")


@dataclass(frozen=True)
class DigestItem:
    title: str
    url: str
    group: str
    source: str
    summary: str = ""
    hot_label: str | None = None
    sort_at: datetime | None = None
    value: int = 1  # 모델이 매긴 학습 가치 1~5


def digest_day(now: datetime) -> date:
    return now.astimezone(KST).date() - timedelta(days=1)


def digest_window(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, KST)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def is_due(now: datetime) -> bool:
    return now.astimezone(KST).hour >= SEND_HOUR_KST


def _rank(item: DigestItem) -> tuple[int, int, int, float]:
    group = _GROUP_ORDER.index(item.group) if item.group in _GROUP_ORDER else len(_GROUP_ORDER)
    newest = -item.sort_at.timestamp() if item.sort_at else 0.0
    return (-item.value, 0 if item.hot_label else 1, group, newest)


def select_items(items: Sequence[DigestItem]) -> list[DigestItem]:
    ranked = sorted(items, key=_rank)
    picked: list[DigestItem] = []
    per_group: Counter[str] = Counter()
    for item in ranked:
        if len(picked) < MAX_ITEMS and per_group[item.group] < MAX_PER_GROUP:
            picked.append(item)
            per_group[item.group] += 1
    for item in ranked:  # 묶음 상한 때문에 자리가 남으면 채운다
        if len(picked) < MAX_ITEMS and item not in picked:
            picked.append(item)
    return sorted(picked, key=_rank)


def _href(url: str) -> str | None:
    # RSS 가 준 값이다. 메일 안 링크로 쓰니 http(s)만 받는다.
    return escape(url, quote=True) if url.startswith(("https://", "http://")) else None


def render_digest(day: date, items: Sequence[DigestItem]) -> tuple[str, str, str]:
    """(제목, 텍스트 본문, HTML 본문)"""
    heading = f"{day.month}월 {day.day}일 AI 기술 소식 {len(items)}건"
    subject = f"[AI 소식] {heading}"
    text_parts = [heading, ""]
    html_parts = [
        '<div style="max-width:640px;font-family:sans-serif;color:#222;line-height:1.6">',
        f'<h2 style="font-size:20px">{escape(heading)}</h2>',
    ]
    for n, item in enumerate(items, 1):
        meta = " · ".join(x for x in (item.source, item.hot_label) if x)
        text_parts += [f"{n}. {item.title}", f"   {meta}"]
        if item.summary:
            text_parts.append(f"   {item.summary}")
        text_parts += [f"   {item.url}", ""]
        href = _href(item.url)
        title = escape(item.title)
        linked = f'<a href="{href}" style="color:#1a56db">{title}</a>' if href else title
        summary = f'<p style="margin:4px 0">{escape(item.summary)}</p>' if item.summary else ""
        html_parts.append(
            '<div style="margin:0 0 20px">'
            f'<div style="font-weight:600">{n}. {linked}</div>'
            f'<div style="font-size:13px;color:#666">{escape(meta)}</div>{summary}</div>'
        )
    html_parts.append("</div>")
    return subject, "\n".join(text_parts), "".join(html_parts)
