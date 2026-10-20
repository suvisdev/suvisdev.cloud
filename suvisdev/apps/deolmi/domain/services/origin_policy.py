"""사이트별 허용 도메인 검증 — 남의 사이트가 공개 키를 가져다 쓰는 것을 막는다."""

from __future__ import annotations


def host_of(value: str) -> str:
    """'https://a.example.com:443/x' 또는 'example.com' → 'a.example.com'."""
    v = value.split("://", 1)[-1].split("/", 1)[0]
    return v.split(":", 1)[0].lower()


def origin_allowed(origin: str | None, domains: tuple[str, ...]) -> bool:
    if not domains:
        return True  # 등록 도메인이 없으면 검증 생략(개발·데모용 키)
    if not origin:
        return False  # 브라우저 호출이면 Origin 헤더가 있어야 한다
    host = host_of(origin)
    for d in domains:
        dh = host_of(d)
        if host == dh or host.endswith("." + dh):  # 정확히 또는 서브도메인
            return True
    return False
