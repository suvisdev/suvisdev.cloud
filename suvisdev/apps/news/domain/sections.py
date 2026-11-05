"""섹션·출처 묶음과 AI 배지 판정 범위 (외부 의존 없는 규칙).

news.suvisdev.cloud 의 목적은 새 AI 기술·아키텍처 변화를 빨리 알아 공부하는 것이다(2026-11-05 사용자 결정).
메인은 AI 섹션(연구소 블로그·논문·릴리스·해설·커뮤니티·국내 AI 매체), 경제 섹션은 부록(경제 언론 RSS + 검색).

AI 배지 판정(rubric.md)은 **한국어 뉴스 기사**에만 쓴다. 기사체 신호(기자명, '-다'체, 인용 표기)를 보기 때문에
영어 글·1차 출처에 돌리면 맞지 않는다 — 11-05 실측: 국내 AI 매체를 뺀 AI 피드 3,321건에서 'AI 생성 의심' 13건
(OpenAI·AWS·Microsoft Research 공식 블로그 포함)과 보류 208건이 나왔다. 같은 날 경제 언론 RSS 982건은 0건.
"""

from __future__ import annotations

SECTIONS: dict[str, str] = {"ai": "AI 기술", "economy": "경제"}
DEFAULT_SECTION = "ai"

# 묶음 코드 → (섹션, 화면 이름). "search" 는 네이버 뉴스 검색 결과(경제 검색어 탭).
GROUPS: dict[str, tuple[str, str]] = {
    "lab": ("ai", "연구소·기업 블로그"),
    "paper": ("ai", "논문"),
    "release": ("ai", "오픈소스 릴리스"),
    "commentary": ("ai", "해설·뉴스레터"),
    "community": ("ai", "커뮤니티"),
    "ko_media": ("ai", "국내 AI 매체"),
    "outlet": ("economy", "경제 언론"),
    "search": ("economy", "뉴스 검색"),
}

JUDGED_GROUPS = frozenset({"ko_media", "outlet", "search"})


def is_section(code: str) -> bool:
    return code in SECTIONS


def section_of_group(group: str) -> str:
    return GROUPS[group][0]


def should_judge(group: str) -> bool:
    """AI 배지 규칙 판정 대상인가 — 한국어 뉴스 기사 묶음만."""
    return group in JUDGED_GROUPS
