"""기사 주소 정규화 — 같은 기사가 추적 파라미터만 달리해 여러 번 저장되지 않게 한다."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "ref", "from", "plink", "cmpid")


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PREFIXES)
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", host, path, urlencode(query), ""))


def domain_of_url(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    for prefix in ("www.", "m.", "mobile."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    return host
