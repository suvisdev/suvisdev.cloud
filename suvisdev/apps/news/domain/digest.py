"""아침 메일 — 어제(한국 시각) 범위, 고르는 순서, 본문 만들기. 외부 의존 없음.

글이 기술 소식인지와 학습 가치는 모델이 정하고(adapter/outbound/llm/ollama_article_classifier.py),
여기서는 그 결과를 우선 주제(11-13 사용자 지시: 새 기술 → 대기업이 쓰는 기술 → 한국·해외 차이)·
학습 가치·화제 수치·출처 순으로 줄 세운다.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from html import escape

from news.domain.glossary import GlossaryTerm

KST = timezone(timedelta(hours=9))
SEND_HOUR_KST = 7
MAX_ITEMS = 10
MAX_PER_GROUP = 4  # 커뮤니티 글이 많아도 메일을 다 차지하지 않게
# 같은 학습 가치면 1차 출처를 앞에 둔다. 논문은 하루 수백 건이라 화제 수치가 있는 것만 후보다(저장소 쿼리).
_GROUP_ORDER = ("lab", "release", "paper", "commentary", "ko_media", "community")
FOCUS_LABELS = {"new_tech": "새 기술", "bigtech": "대기업 적용", "korea_global": "한국·해외 차이"}
_FOCUS_ORDER = tuple(FOCUS_LABELS)


@dataclass(frozen=True)
class Explanation:
    """모델이 쓴 기사 풀이·분석(11-16 사용자 요청). 틀릴 수 있어 메일에 그렇게 밝힌다."""

    easy: str  # 쉽게 말하면
    why: str  # 왜 중요한가
    pros: tuple[str, ...]  # 이점
    cons: tuple[str, ...]  # 단점·한계
    from_page: bool  # 원문 본문을 읽었는지 — False 면 RSS 요약만 보고 쓴 것


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
    focus: str = "none"  # 모델이 고른 우선 주제(FOCUS_LABELS 키 또는 none)
    explanation: Explanation | None = None
    terms: tuple[GlossaryTerm, ...] = ()  # 검수 사전(glossary.json)의 용어 뜻


def digest_day(now: datetime) -> date:
    return now.astimezone(KST).date() - timedelta(days=1)


def digest_window(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, KST)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def is_due(now: datetime) -> bool:
    return now.astimezone(KST).hour >= SEND_HOUR_KST


def _rank(item: DigestItem) -> tuple[int, int, int, int, float]:
    focus = _FOCUS_ORDER.index(item.focus) if item.focus in _FOCUS_ORDER else len(_FOCUS_ORDER)
    group = _GROUP_ORDER.index(item.group) if item.group in _GROUP_ORDER else len(_GROUP_ORDER)
    newest = -item.sort_at.timestamp() if item.sort_at else 0.0
    return (focus, -item.value, 0 if item.hot_label else 1, group, newest)


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


_NOTE = "풀이·분석은 노트북 EXAONE 7.8B가 쓴 것이라 틀릴 수 있습니다. 숫자와 사실은 원문에서 확인하세요."


def _explanation_text(item: DigestItem) -> list[str]:
    lines: list[str] = []
    ex = item.explanation
    if ex:
        lines.append(f"   쉽게 말하면: {ex.easy}")
        if ex.why:
            lines.append(f"   왜 중요한가: {ex.why}")
        lines += [f"   이점: {p}" for p in ex.pros]
        lines += [f"   단점·한계: {c}" for c in ex.cons]
        if not ex.from_page:
            lines.append("   (원문을 못 읽어 요약만 보고 분석함)")
    lines += [f"   용어 {t.term}: {t.desc}" for t in item.terms]
    return lines


def _ul(label: str, rows: Sequence[str]) -> str:
    if not rows:
        return ""
    lis = "".join(f"<li>{escape(r)}</li>" for r in rows)
    return f'<div style="margin-top:6px"><b>{label}</b><ul style="margin:2px 0 0 18px;padding:0">{lis}</ul></div>'


def _explanation_html(item: DigestItem) -> str:
    parts: list[str] = []
    ex = item.explanation
    if ex:
        parts.append(f'<p style="margin:6px 0"><b>쉽게 말하면</b> {escape(ex.easy)}</p>')
        if ex.why:
            parts.append(f'<p style="margin:6px 0"><b>왜 중요한가</b> {escape(ex.why)}</p>')
        parts += [_ul("이점", ex.pros), _ul("단점·한계", ex.cons)]
        if not ex.from_page:
            parts.append(
                '<div style="font-size:12px;color:#888">원문을 못 읽어 요약만 보고 분석함</div>'
            )
    parts.append(_ul("용어", [f"{t.term}: {t.desc}" for t in item.terms]))
    body = "".join(parts)
    return (
        f'<div style="background:#f6f7f9;padding:8px 12px;margin-top:6px;font-size:14px">{body}</div>'
        if body
        else ""
    )


def render_digest(
    day: date, items: Sequence[DigestItem], trend: Sequence[str] = ()
) -> tuple[str, str, str]:
    """(제목, 텍스트 본문, HTML 본문)"""
    heading = f"{day.month}월 {day.day}일 AI 기술 소식 {len(items)}건"
    subject = f"[AI 소식] {heading}"
    text_parts = [heading, ""]
    html_parts = [
        '<div style="max-width:640px;font-family:sans-serif;color:#222;line-height:1.6">',
        f'<h2 style="font-size:20px">{escape(heading)}</h2>',
    ]
    if trend:
        text_parts += ["오늘의 흐름", *[f"- {t}" for t in trend], ""]
        html_parts.append(f'<div style="margin-bottom:20px">{_ul("오늘의 흐름", trend)}</div>')
    for n, item in enumerate(items, 1):
        tag = FOCUS_LABELS.get(item.focus)
        meta = " · ".join(x for x in (tag, item.source, item.hot_label) if x)
        text_parts += [f"{n}. {item.title}", f"   {meta}"]
        if item.summary:
            text_parts.append(f"   {item.summary}")
        text_parts += _explanation_text(item)
        text_parts += [f"   {item.url}", ""]
        href = _href(item.url)
        title = escape(item.title)
        linked = f'<a href="{href}" style="color:#1a56db">{title}</a>' if href else title
        summary = f'<p style="margin:4px 0">{escape(item.summary)}</p>' if item.summary else ""
        html_parts.append(
            '<div style="margin:0 0 24px">'
            f'<div style="font-weight:600">{n}. {linked}</div>'
            f'<div style="font-size:13px;color:#666">{escape(meta)}</div>{summary}'
            f"{_explanation_html(item)}</div>"
        )
    if any(item.explanation for item in items) or trend:
        text_parts.append(_NOTE)
        html_parts.append(f'<p style="font-size:12px;color:#888">{escape(_NOTE)}</p>')
    html_parts.append("</div>")
    return subject, "\n".join(text_parts), "".join(html_parts)
