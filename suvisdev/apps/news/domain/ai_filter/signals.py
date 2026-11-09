"""기사에서 규칙 신호를 뽑는다. 표준 라이브러리만 쓴다.

기사 필드: id, title, summary(검색 API·RSS 요약), body(RSS 가 직접 준 본문, 없으면 비움),
source(매체명), url, author(선택), published_at(선택)
신호 정의는 newsdesk 하네스 references/rubric.md 가 원천이다. 코드를 바꾸면 rubric 표도 같이 고친다.
이 파일은 suvisdev.cloud 저장소 apps/news/domain/ai_filter/ 와 newsdesk 하네스 scripts/ai_filter/ 에 같은 내용으로 있다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

Article = Mapping[str, Any]
Signal = dict[str, str]
Metrics = dict[str, Any]

# ⑤ AI 생성 흔적 ─────────────────────────────────────────────
# 작성 고지는 본문 앞뒤·제목·요약·작성자 필드에서만 본다. 본문 중간의 AI 언급은 기사 주제일 수 있다.
DISCLOSURE = re.compile(
    r"(이|본|해당)\s*기사는.{0,40}(AI|인공지능|생성형|알고리즘|자동화?\s*시스템|로봇).{0,30}(작성|생성|제작|만들)"
    r"|※.{0,60}(AI|인공지능|생성형).{0,30}(작성|생성|활용)"
    r"|(AI|인공지능|로봇)\s*기자\s*(=|\]|\)|$)"
    r"|^\s*\[?(AI|인공지능|로봇)\s*기자"
    r"|자동\s*(생성|작성)\s*(된|한)?\s*기사",
    re.M,
)
AUTHOR_AI = re.compile(r"AI|인공지능|로봇|자동|bot", re.I)

PROMPT_LEFTOVER = re.compile(
    r"^\s*(물론(입니다|이죠)|네,\s*알겠습니다|좋습니다[.!])"
    r"|다음은\s.{0,40}(기사|요약|초안)입니다"
    r"|(요청하신|말씀하신)\s*(기사|내용|주제)"
    r"|AI\s*언어\s*모델(로서|로써)|As an AI|I cannot"
    r"|\[(기자\s*이름|기자명|날짜|출처|회사명|이름|매체명)\]"
    r"|\{\{[^}]+\}\}"
    r"|도움이\s*(되셨기를|되었으면)\s*(바랍니다|합니다)",
    re.M | re.I,
)

MD_BOLD = re.compile(r"\*\*[^*\n]{1,80}\*\*")
MD_HEAD = re.compile(r"^\s{0,3}#{1,4}\s+\S", re.M)
# 글머리표(-, *, •)만 센다. ▲ 목록과 번호 목록(1., 01.)은 국내 기사·방송 요약에 흔해 세지 않는다
# (2026-11-05 실측: 번호 목록을 세었더니 SBS 방송 요약 3건이 AI 생성 의심으로 잘못 표시됨)
MD_BULLET = re.compile(r"^\s*[-*•]\s+\S", re.M)

# "OOO 기자입니다"(방송 맺음말)는 잡고 "기자회견·기자단"은 거른다
BYLINE = re.compile(
    r"[가-힣]{2,4}\s*(?:기자|특파원|논설위원|선임기자|객원기자|에디터)(?:입니다|였습니다)?(?![가-힣])"
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

AI_CLICHE = (
    "결론적으로",
    "요약하자면",
    "정리하자면",
    "알아보겠습니다",
    "살펴보겠습니다",
    "알아보자",
    "살펴보자",
    "중요한 역할을",
    "다양한 측면",
    "주목할 만한",
    "주목할 만합니다",
    "시사하는 바가 크",
    "것이 중요합니다",
    "무엇일까요",
    "궁금하신",
    "총정리",
    "꿀팁",
    "이 글에서는",
    "이번 글에서는",
    "마무리하며",
    "다음과 같습니다",
    "도움이 되",
)

# ④ 근거 충실성 ──────────────────────────────────────────────
QUOTE = re.compile(r"[“\"]([^”\"]{6,300})[”\"]\s*(?:라고|이라고|고|며|면서)")
ATTRIB = re.compile(
    r"에\s*따르면|(?:말|설명|강조|지적|주장|발표|공개|언급|답|확인|보고)했다|밝혔다|전했다|덧붙였다"
    r"|집계됐다|조사\s*결과|통계청|보도자료"
)

# ③ 표현 특징 (배지 전용) ────────────────────────────────────
CLICKBAIT = re.compile(
    r"충격|경악|발칵|난리|헉|소름|대박|결국\s|이럴\s*수가|알고\s*보니|아무도\s*몰랐던|\?!|!{2,}|…$|\.\.\.$"
)

# 배지를 누르면 보이는 문구. 단정하지 않고 관찰한 사실만 쓴다 (rubric.md §3 화면 문구)
REASON_KO = {
    "AI_DISCLOSURE": "매체가 AI로 작성했다고 밝힘",
    "PROMPT_LEFTOVER": "AI 대화 문장이 본문에 남아 있음",
    "MARKDOWN": "기사에 쓰지 않는 마크다운 서식",
    "REWRITE_SUSPECT": "다른 매체 기사와 본문이 많이 겹침",
    "NO_BYLINE": "기자 이름이 없음",
    "POLITE_REGISTER": "기사체가 아닌 '-습니다'체",
    "AI_CLICHE": "AI 글에 자주 나오는 표현이 많음",
    "NO_EVIDENCE": "인용이나 출처 표기가 없음",
    "UNKNOWN_SOURCE": "확인되지 않은 매체",
    "BLOCKED_SOURCE": "운영자가 차단한 매체",
}

WORD = re.compile(r"[가-힣A-Za-z0-9]{2,}")
SENT = re.compile(r"([가-힣]+)\s*[.!?](?=\s|$|[”\"])")


def domain_of(article: Article) -> str:
    host = urlparse(str(article.get("url") or "")).netloc.lower()
    for p in ("www.", "m.", "mobile."):
        if host.startswith(p):
            host = host[len(p) :]
    return host


def _sig(code: str, axis: str, strength: str, evidence: str = "") -> Signal:
    return {"code": code, "axis": axis, "strength": strength, "evidence": evidence[:80]}


def _first(rx: re.Pattern[str], text: str) -> str | None:
    m = rx.search(text)
    return m.group(0) if m else None


def _match_domain(dom: str, items: Sequence[str]) -> bool:
    return any(dom == d or dom.endswith("." + d) for d in items)


def article_signals(
    a: Article,
    th: Mapping[str, Any],
    sources: Mapping[str, Sequence[str]],
    use_body: bool = True,
    use_source: bool = True,
) -> tuple[list[Signal], Metrics]:
    """기사 1건 → (신호 목록, 측정값). use_body/use_source 로 실험 A·B·C 를 나눈다.

    body 가 비어 있으면(요약만 있으면) ④⑤축의 본문 신호는 보지 않는다(n/a). 요약에는 기자명·인용이
    원래 없어서, 보면 모든 기사에 NO_BYLINE 이 켜진다. strong 신호(작성 고지·프롬프트 잔재)는
    제목·요약에서도 본다.
    """
    title = str(a.get("title") or "").strip()
    summary = str(a.get("summary") or "").strip() if use_body else ""
    body = str(a.get("body") or "").strip() if use_body else ""
    author = str(a.get("author") or "").strip()
    sigs: list[Signal] = []
    m: Metrics = {"body_chars": len(body)}

    head, tail = body[: th["head_chars"]], body[-th["tail_chars"] :]

    # ⑤ strong
    hit = (
        (author if AUTHOR_AI.search(author) and "기자" in author else None)
        or _first(DISCLOSURE, head)
        or _first(DISCLOSURE, tail)
        or _first(DISCLOSURE, title)
        or _first(DISCLOSURE, summary)
    )
    if hit:
        sigs.append(_sig("AI_DISCLOSURE", "ai_trace", "strong", hit))
    hit = _first(PROMPT_LEFTOVER, "\n".join((title, summary, body)))
    if hit:
        sigs.append(_sig("PROMPT_LEFTOVER", "ai_trace", "strong", hit))

    if body:
        # ⑤ medium
        bold = len(MD_BOLD.findall(body))
        heads = len(MD_HEAD.findall(body))
        bullets = len(MD_BULLET.findall(body))
        m.update(md_bold=bold, md_head=heads, md_bullet=bullets)
        if bold or heads or bullets >= th["bullet_min"]:
            sigs.append(
                _sig(
                    "MARKDOWN",
                    "ai_trace",
                    "medium",
                    f"굵게 {bold} · 제목 {heads} · 글머리 {bullets}",
                )
            )

        has_byline = bool(author) or bool(
            BYLINE.search(head) or BYLINE.search(tail) or EMAIL.search(tail)
        )
        m["byline"] = has_byline
        if not has_byline:
            sigs.append(_sig("NO_BYLINE", "ai_trace", "medium", "작성자·기자명·이메일 없음"))

        ends = SENT.findall(body)
        polite = sum(1 for w in ends if w.endswith(("니다", "니까", "요", "죠")))
        plain = sum(1 for w in ends if w.endswith("다") and not w.endswith("니다"))
        m.update(sent_polite=polite, sent_plain=plain)
        total = polite + plain
        if total >= th["polite_min_sentences"] and polite / total >= th["polite_ratio"]:
            sigs.append(
                _sig("POLITE_REGISTER", "ai_trace", "medium", f"-습니다체 {polite}/{total}")
            )

        cl = [c for c in AI_CLICHE if c in body]
        m["cliche_hits"] = len(cl)
        if len(cl) >= th["cliche_min_hits"]:
            sigs.append(_sig("AI_CLICHE", "ai_trace", "medium", ", ".join(cl[:4])))

        # ④
        quotes, attrib = len(QUOTE.findall(body)), len(ATTRIB.findall(body))
        m.update(quotes=quotes, attributions=attrib)
        if len(body) >= th["min_body_chars_for_evidence"] and quotes + attrib == 0:
            sigs.append(_sig("NO_EVIDENCE", "evidence", "medium", "인용·출처 표기 0개"))

        # ③ 제목-본문 일치
        if len(body) >= th["min_body_chars_for_style"]:
            words = WORD.findall(title)
            if words:
                overlap = sum(1 for w in words if w[:2] in body) / len(words)
                m["title_overlap"] = round(overlap, 2)
                if overlap < th["title_overlap_min"]:
                    sigs.append(
                        _sig(
                            "TITLE_BODY_MISMATCH", "style", "weak", f"제목 단어 일치 {overlap:.0%}"
                        )
                    )

    hit = _first(CLICKBAIT, title)
    if hit:
        sigs.append(_sig("CLICKBAIT", "style", "weak", hit))

    # ②
    if use_source:
        dom = domain_of(a)
        m["domain"] = dom
        if dom and _match_domain(dom, sources.get("blocked", [])):
            sigs.append(_sig("BLOCKED_SOURCE", "source", "strong", dom))
        elif not dom or not _match_domain(dom, sources.get("known", [])):
            sigs.append(_sig("UNKNOWN_SOURCE", "source", "medium", dom or "도메인 없음"))

    return sigs, m


# 배치 신호: 교차 보도, 재가공 ────────────────────────────────


def ngrams(text: str, n: int) -> set[str]:
    t = re.sub(r"\s+", "", text)
    return {t[i : i + n] for i in range(max(len(t) - n + 1, 0))}


def jaccard(x: set[str], y: set[str]) -> float:
    return len(x & y) / len(x | y) if x and y else 0.0


def batch_signals(
    articles: Sequence[Article],
    per: dict[str, dict[str, Any]],
    th: Mapping[str, Any],
    sources: Mapping[str, Sequence[str]],
) -> None:
    """같은 사건 묶음을 만들고 CROSSCHECKED·REWRITE_SUSPECT 를 per[id] 신호에 더한다 (C 모드 전용)."""
    ids = [str(a["id"]) for a in articles]
    tg = {str(a["id"]): ngrams(str(a.get("title") or ""), 2) for a in articles}
    bg = {str(a["id"]): ngrams(str(a.get("body") or ""), 5) for a in articles}
    dom = {str(a["id"]): domain_of(a) for a in articles}
    known_list = sources.get("known", [])
    known = {i: bool(dom[i]) and _match_domain(dom[i], known_list) for i in ids}

    parent = {i: i for i in ids}

    def find(i: str) -> str:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            i, j = ids[x], ids[y]
            if dom[i] != dom[j] and (
                jaccard(tg[i], tg[j]) >= th["cluster_title_jaccard"]
                or jaccard(bg[i], bg[j]) >= th["rewrite_body_jaccard"]
            ):
                parent[find(i)] = find(j)
                # 재가공: 미확인 매체 기사가 알려진 매체 기사와 본문이 많이 겹친다
                for a, b in ((i, j), (j, i)):
                    sim = jaccard(bg[a], bg[b])
                    if not known[a] and known[b] and sim >= th["rewrite_body_jaccard"]:
                        per[a]["signals"].append(
                            _sig(
                                "REWRITE_SUSPECT",
                                "ai_trace",
                                "medium",
                                f"{dom[b]} 와 본문 유사도 {sim:.2f}",
                            )
                        )

    clusters: dict[str, set[str]] = {}
    for i in ids:
        clusters.setdefault(find(i), set()).add(dom[i])
    for i in ids:
        others = clusters[find(i)] - {dom[i], ""}
        others_known = {d for d in others if _match_domain(d, known_list)}
        per[i]["metrics"]["crosscheck_domains"] = len(others)
        # 콘텐츠 농장끼리 서로 베낀 것은 교차 보도로 치지 않는다 — 알려진 매체가 1곳 이상 있어야 한다
        if others_known:
            per[i]["signals"].append(
                _sig("CROSSCHECKED", "source", "positive", ", ".join(sorted(others_known))[:80])
            )
