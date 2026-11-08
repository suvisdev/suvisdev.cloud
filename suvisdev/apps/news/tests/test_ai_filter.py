"""규칙 판정기 — newsdesk 하네스 합성 기사 17건 회귀 (가상 매체·가상 도시, 실제 기사 아님).

이 수치는 성능이 아니다. 합성 기사는 규칙을 보고 만들었다. 결정표가 바뀌었는지만 본다."""

import json
from collections import Counter
from pathlib import Path

from news.domain.ai_filter import classify

_FIX = Path(__file__).parent / "fixtures"


def _load():
    rows = [
        json.loads(x)
        for x in (_FIX / "synthetic.jsonl").read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    sources = json.loads((_FIX / "sources.fixture.json").read_text(encoding="utf-8"))
    return rows, sources


def test_synthetic_confusion_matrix_c_mode():
    rows, sources = _load()
    sure = [r for r in rows if not r.get("unsure")]
    res = {r["id"]: r for r in classify(sure, "C", sources)}
    cm = Counter((r["label"], res[r["id"]]["verdict"]) for r in sure)
    assert (
        cm[("normal", "normal")] == 8
        and cm[("normal", "ai")] == 0
        and cm[("normal", "pending")] == 0
    )
    assert cm[("ai", "ai")] == 7 and cm[("ai", "pending")] == 1  # f16 가짜 기자명만 보류


def test_badges_split_disclosed_and_suspected():
    rows, sources = _load()
    res = {r["id"]: r for r in classify(rows, "C", sources)}
    assert res["f03"]["badge"] == "ai_disclosed"  # ※ 생성형 AI 활용 고지
    assert res["f13"]["badge"] == "ai_disclosed"  # 작성자 'AI 기자'
    assert res["f05"]["badge"] == "ai_suspected"
    assert "기사에 쓰지 않는 마크다운 서식" in res["f05"]["reasons_ko"]
    assert res["f08"]["badge"] == "none"  # AI 를 주제로 다룬 기사는 표시 대상 아님
    assert res["f16"]["badge"] == "none"  # pending 은 배지 없음


def test_summary_only_article_has_no_body_signals():
    """검색 API·RSS 요약만 있으면 기자명·인용이 원래 없다 — 본문 신호를 켜지 않는다."""
    art = {
        "id": "s1",
        "title": "가나시 도서관 야간 운영",
        "summary": "가나시 시립도서관이 다음 달부터 평일 밤 10시까지 문을 연다.",
        "url": "https://unknown.example/1",
    }
    (r,) = classify([art], "C", {"known": [], "blocked": []})
    codes = {s["code"] for s in r["signals"]}
    assert "NO_BYLINE" not in codes and "NO_EVIDENCE" not in codes
    assert r["verdict"] == "normal" and r["axes"]["ai_trace"] == "n/a"


def test_disclosure_in_summary_is_caught():
    art = {
        "id": "s2",
        "title": "주말 날씨 맑음",
        "summary": "전국이 맑겠다. 본 기사는 인공지능이 기상 자료를 바탕으로 작성했습니다.",
        "url": "https://unknown.example/2",
    }
    (r,) = classify([art], "C", {"known": [], "blocked": []})
    assert r["verdict"] == "ai" and r["badge"] == "ai_disclosed"
