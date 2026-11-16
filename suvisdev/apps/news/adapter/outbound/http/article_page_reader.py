"""메일 풀이용 원문 본문 받기(11-16). RSS 요약은 300자 안팎이라 이것만으로는 분석이 추측이 된다.

막는 곳(11-16 확인: news.hada.io 403)은 우회하지 않고 빈 문자열을 돌려준다 — 풀이는 요약만 보고 쓰고 메일에 그렇게 밝힌다.
주소는 Hacker News 등 누구나 올리는 링크라, 내부 주소(사설·루프백 등)로 가는 요청과 리다이렉트는 막고 받는 크기를 제한한다.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from news.adapter.outbound.http.rss_feed_reader import USER_AGENT
from news.app.ports.output.news_digest_ports import ArticlePageReaderPort

logger = logging.getLogger(__name__)

MAX_CHARS = 3000  # 7.8B num_ctx 4096 안에 지시문·요약과 함께 들어가게
MAX_BYTES = 2_000_000  # 압축 응답은 받지 않으니 받은 바이트 = 메모리
MAX_REDIRECTS = 3
TOTAL_TIMEOUT_S = 20.0  # 조금씩 끝없이 보내는 서버가 메일을 붙잡지 않게 — DNS 부터 본문까지 전부
_DROP = ("script", "style", "nav", "header", "footer", "aside", "form", "noscript")


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_DROP):
        tag.decompose()
    root = soup.find("article") or soup.body or soup
    # 메뉴·버튼 같은 짧은 조각은 뺀다
    paras = (p.get_text(" ", strip=True) for p in root.find_all(["p", "li", "h2", "h3"]))
    return "\n".join(p for p in paras if len(p) > 30)[:MAX_CHARS]


@dataclass(frozen=True)
class _Pinned:
    """확인한 IP 로 연결할 요청. Host 헤더와 TLS 이름(SNI·인증서 확인)은 원래 도메인을 쓴다."""

    url: str
    host_header: str
    hostname: str


async def pin_public(url: str) -> _Pinned | None:
    """http(s)이고 호스트 주소가 전부 공인 주소면 그중 하나로 고정한 요청, 아니면 None.
    한 번 조회한 IP 로 직접 연결해 검사 뒤 DNS 를 바꾸는 우회(rebinding)를 막는다."""
    try:
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return None
        infos = await asyncio.to_thread(socket.getaddrinfo, parts.hostname, port)
        ips = [ipaddress.ip_address(info[4][0]) for info in infos]
    except (OSError, UnicodeError, ValueError):
        return None
    if not ips or not all(ip.is_global for ip in ips):
        return None
    host = f"[{ips[0]}]" if ips[0].version == 6 else str(ips[0])
    path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
    return _Pinned(
        f"{parts.scheme}://{host}:{port}{path}", parts.netloc.rsplit("@", 1)[-1], parts.hostname
    )


class HttpArticlePageReader(ArticlePageReaderPort):
    def __init__(
        self, *, timeout: float = 10.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._timeout = timeout
        self._transport = transport

    async def read(self, url: str) -> str:
        # 남의 사이트 응답은 무엇이든 올 수 있다(잘못된 주소·charset=base64_codec 등). 원문은 덤이니
        # 어떤 실패도 빈 문자열로 바꿔 메일이 멈추지 않게 한다 — 예외를 하나씩 막다 계속 새서(11-16 리뷰 4회) 경계에서 받는다.
        try:
            return await asyncio.wait_for(self._read(url), TOTAL_TIMEOUT_S)
        except Exception as e:  # noqa: BLE001
            logger.info("[news] 원문 못 읽음 — 요약만으로 풀이: %s", type(e).__name__)
            return ""

    async def _read(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            for _ in range(MAX_REDIRECTS + 1):
                pinned = await pin_public(url)
                if pinned is None:
                    return ""
                async with client.stream(
                    "GET",
                    pinned.url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Host": pinned.host_header,
                        "Accept-Encoding": "identity",
                    },
                    extensions={"sni_hostname": pinned.hostname},
                ) as res:
                    if res.is_redirect and "location" in res.headers:
                        url = urljoin(url, res.headers["location"])
                        continue
                    if res.status_code != 200 or "html" not in res.headers.get("content-type", ""):
                        return ""
                    # 압축을 풀면 몇 KB 가 수백 MB 가 될 수 있다 — 그래도 압축해 보내는 곳은 건너뛴다
                    if res.headers.get("content-encoding", "identity") != "identity":
                        return ""
                    return extract_text(await _read_limited(res))
        return ""


async def _read_limited(res: httpx.Response) -> str:
    chunks: list[bytes] = []
    size = 0
    async for chunk in res.aiter_bytes():  # 압축 응답은 위에서 걸렀으니 푸는 일 없음
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_BYTES:
            break
    return b"".join(chunks)[:MAX_BYTES].decode(res.encoding or "utf-8", errors="replace")
