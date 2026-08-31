"""한글 자모 분해 + 편집거리 기반 퍼지 매칭.

'쩸' → 'ㅉㅐㅁ', '잼' → 'ㅈㅐㅁ' — 편집거리 1.
제목 검색 0건일 때만 폴백으로 사용한다.
"""

from __future__ import annotations

_CHO = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
_JUNG = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
_JONG = [""] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")

_HANGUL_BASE = 0xAC00
_HANGUL_END = 0xD7A3


def decompose(text: str) -> str:
    """한글을 자모 단위로 분해한다. 비한글 문자는 그대로 둔다."""
    result: list[str] = []
    for ch in text:
        cp = ord(ch)
        if _HANGUL_BASE <= cp <= _HANGUL_END:
            offset = cp - _HANGUL_BASE
            cho = offset // (21 * 28)
            jung = (offset % (21 * 28)) // 28
            jong = offset % 28
            result.append(_CHO[cho])
            result.append(_JUNG[jung])
            if jong:
                result.append(_JONG[jong])
        else:
            result.append(ch)
    return "".join(result)


def edit_distance(a: str, b: str) -> int:
    """레벤슈타인 편집거리."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1] + [0] * len(b)
        for j, cb in enumerate(b):
            curr[j + 1] = min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (0 if ca == cb else 1),
            )
        prev = curr
    return prev[-1]


def fuzzy_match_titles(
    query: str, titles: list[tuple[int, str]], *, max_distance: int = 3
) -> list[tuple[int, str, int]]:
    """query와 가장 유사한 제목을 찾는다.

    Returns: [(movie_id, title, distance), ...] 거리순 정렬, max_distance 이하만.
    """
    q_jamo = decompose(query.replace(" ", "").lower())
    if not q_jamo:
        return []

    results: list[tuple[int, str, int]] = []
    for movie_id, title in titles:
        t_jamo = decompose(title.replace(" ", "").lower())
        # 길이 차이가 max_distance보다 크면 스킵 (편집거리 하한)
        if abs(len(q_jamo) - len(t_jamo)) > max_distance:
            continue
        d = edit_distance(q_jamo, t_jamo)
        if d <= max_distance:
            results.append((movie_id, title, d))

    results.sort(key=lambda x: x[2])
    return results[:5]
