"""아침 메일 풀이·분석(11-16) — 풀이가 메일에 들어가는지, 모델이 멈춰도 메일은 나가는지, 원문 읽기·출력 해석."""

import asyncio
import gzip
import ipaddress
import json
import socket
import time
from datetime import date

import httpx
import pytest
from news_fakes import FakeRepo
from test_digest import NOW, _article, _Classifier, _Ledger, _Mailer

from news.adapter.outbound.http import article_page_reader as page_reader_module
from news.adapter.outbound.http.article_page_reader import HttpArticlePageReader, extract_text
from news.adapter.outbound.llm.ollama_article_explainer import (
    OllamaArticleExplainer,
    build_explain_prompt,
    parse_explanation,
)
from news.app.ports.output.news_digest_ports import (
    ArticleExplainerPort,
    ArticlePageReaderPort,
    ClassifierUnavailableError,
)
from news.app.use_cases.news_digest_interactor import NewsDigestInteractor
from news.domain.digest import DigestItem, Explanation, render_digest
from news.domain.glossary import GlossaryTerm

EX = Explanation(
    easy="비를 더 잘 맞힌다",
    why="재난 대비",
    pros=("정확도 30% 향상",),
    cons=("<지역> 편차는 모름",),
    from_page=False,
)


class _Reader(ArticlePageReaderPort):
    async def read(self, url: str) -> str:
        return f"본문:{url}"


class _Explainer(ArticleExplainerPort):
    def __init__(self, down_after: int | None = None) -> None:
        self.down_after, self.calls = down_after, 0

    async def explain(self, item: DigestItem, page_text: str) -> Explanation | None:
        if self.down_after is not None and self.calls >= self.down_after:
            raise ClassifierUnavailableError("꺼짐")
        self.calls += 1
        # 받은 원문을 풀이에 넣어 메일에서 확인한다
        return Explanation(f"{item.title} 풀이 [{page_text}]", "중요", ("이점",), ("단점",), True)

    async def trend(self, items):
        return ["오늘은 강수 예측"]


async def _send(titles, explainer):
    repo, mailer, ledger = FakeRepo(), _Mailer(), _Ledger()
    repo.digest_candidates = [_article(n, t) for n, t in enumerate(titles, 1)]
    use_case = NewsDigestInteractor(
        repo, _Classifier(), mailer, ledger, page_reader=_Reader(), explainer=explainer
    )
    report = await use_case.send_if_due(NOW)
    return report, mailer.sent[0][1], ledger


def test_render_shows_explanation_terms_trend_and_note():
    item = DigestItem(
        title="강수",
        url="https://a/1",
        group="lab",
        source="s",
        explanation=EX,
        terms=(GlossaryTerm("RAG (검색 증강 생성)", "검색해 답한다"),),
    )
    _, text, html = render_digest(date(2026, 11, 15), [item], ["흐름 한 줄"])
    for part in (
        "오늘의 흐름",
        "흐름 한 줄",
        "쉽게 말하면: 비를 더 잘 맞힌다",
        "왜 중요한가: 재난 대비",
        "이점: 정확도 30% 향상",
        "단점·한계: <지역> 편차는 모름",
        "요약만 보고 분석함",
        "용어 RAG (검색 증강 생성): 검색해 답한다",
        "틀릴 수 있습니다",
    ):
        assert part in text
    assert "&lt;지역&gt;" in html and "<지역>" not in html


def test_render_without_explanation_has_no_note():
    _, text, _ = render_digest(date(2026, 11, 15), [DigestItem("t", "https://a", "lab", "s")])
    assert "틀릴 수 있습니다" not in text and "오늘의 흐름" not in text


@pytest.mark.asyncio
async def test_mail_has_explanation_from_page_terms_and_trend():
    report, text, _ = await _send(["RAG 새 기법", "다른 글"], _Explainer())
    assert report.status == "sent"
    assert "RAG 새 기법 풀이 [본문:https://a.example/1]" in text
    assert "다른 글 풀이 [본문:https://a.example/2]" in text
    assert "오늘은 강수 예측" in text and "용어 RAG (검색 증강 생성)" in text


@pytest.mark.asyncio
async def test_explainer_down_still_sends_with_done_parts():
    report, text, ledger = await _send(["첫 글", "둘째 글"], _Explainer(down_after=1))
    assert report.status == "sent" and len(ledger.finished) == 1
    assert text.count(" 풀이 [") == 1 and "오늘의 흐름" not in text


def test_parse_explanation_needs_easy_and_trims_points():
    assert parse_explanation({"why": "x"}, from_page=True) is None
    assert parse_explanation({"easy": "  "}, from_page=True) is None
    ex = parse_explanation(
        {"easy": " 쉬움 ", "why": 3, "pros": ["a", "", 1, "b", "c", "d"], "cons": "x"},
        from_page=True,
    )
    assert ex == Explanation("쉬움", "", ("a", "b", "c"), (), True)


def test_explain_prompt_says_when_page_missing():
    item = DigestItem("제목", "https://a", "lab", "출처", summary="요약")
    assert "원문:\n본문" in build_explain_prompt(item, "본문")
    assert "못 읽음" in build_explain_prompt(item, "")


def _ollama(content: str = "", status: int = 200) -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda req: httpx.Response(status, json={"message": {"content": content}})
    )


@pytest.mark.asyncio
async def test_explainer_parses_model_output_and_raises_on_server_error():
    item = DigestItem("제목", "https://a", "lab", "출처")
    ok = OllamaArticleExplainer(
        base_url="http://o", transport=_ollama(json.dumps({"easy": "풀이", "pros": ["p"]}))
    )
    ex = await ok.explain(item, "")
    assert ex is not None and ex.pros == ("p",) and not ex.from_page
    bad = OllamaArticleExplainer(base_url="http://o", transport=_ollama("not json"))
    assert await bad.explain(item, "본문") is None and await bad.trend([item]) == []
    down = OllamaArticleExplainer(base_url="http://o", transport=_ollama(status=500))
    with pytest.raises(ClassifierUnavailableError):
        await down.explain(item, "")


def test_extract_text_keeps_article_paragraphs_only():
    html = (
        "<html><body><nav><p>메뉴 메뉴 메뉴 메뉴 메뉴 메뉴 메뉴 메뉴 메뉴 메뉴 메뉴</p></nav>"
        "<article><p>짧음</p><p>구글 딥마인드가 강수 탐지 정확도를 30% 이상 높였다고 밝혔다.</p>"
        "<script>var x = 'script script script script script script';</script></article></body></html>"
    )
    assert extract_text(html) == "구글 딥마인드가 강수 탐지 정확도를 30% 이상 높였다고 밝혔다."


_DNS = {
    "pub.example": "93.184.216.34",
    "evil.example": "93.184.216.35",
    "inner.example": "10.0.0.5",
}


@pytest.fixture
def fake_dns(monkeypatch):
    def getaddrinfo(host, port, *a, **k):
        if host in _DNS:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (_DNS[host], port))]
        try:
            ipaddress.ip_address(host)
        except ValueError:
            raise socket.gaierror("unknown") from None
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]

    monkeypatch.setattr(page_reader_module.socket, "getaddrinfo", getaddrinfo)


def _site(req: httpx.Request) -> httpx.Response:
    html = {"content-type": "text/html"}
    if req.url.path == "/blocked":
        return httpx.Response(403, text="no")
    if req.url.path == "/pdf":
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%")
    if req.url.path == "/to-inner":
        return httpx.Response(302, headers={"location": "http://inner.example/admin"})
    if req.url.path == "/to-ok":
        return httpx.Response(302, headers={"location": "/ok"})
    if req.url.host == "inner.example":
        return httpx.Response(200, headers=html, text="<article><p>" + "내부 비밀 " * 10)
    return httpx.Response(200, headers=html, text="<article><p>" + "본문 문장입니다. " * 5)


@pytest.mark.asyncio
async def test_page_reader_returns_empty_when_blocked_or_not_html(fake_dns):
    reader = HttpArticlePageReader(transport=httpx.MockTransport(_site))
    assert await reader.read("https://pub.example/blocked") == ""
    assert await reader.read("https://pub.example/pdf") == ""
    assert await reader.read("ftp://pub.example/x") == ""
    assert (await reader.read("https://pub.example/ok")).startswith("본문 문장입니다.")
    assert (await reader.read("https://pub.example/to-ok")).startswith("본문 문장입니다.")


@pytest.mark.asyncio
async def test_page_reader_never_requests_internal_addresses(fake_dns):
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(f"{req.url.host} {req.headers['host']}")
        return _site(req)

    reader = HttpArticlePageReader(transport=httpx.MockTransport(handler))
    for url in (
        "http://127.0.0.1/x",
        "http://10.0.0.5/x",
        "http://inner.example/x",
        "http://[::1]/x",
        "http://169.254.169.254/latest",
        "https://nowhere.example/x",
        "http://pub.example:bad/x",
    ):
        assert await reader.read(url) == ""
    assert seen == []
    assert await reader.read("https://evil.example/to-inner") == ""
    assert seen == ["93.184.216.35 evil.example"]


@pytest.mark.asyncio
async def test_page_reader_connects_to_checked_ip_with_original_host(monkeypatch):
    """검사 때는 공인 IP, 다음 조회부터 내부 IP를 주는 DNS(rebinding)여도 검사한 IP로만 연결한다."""
    answers = iter(["93.184.216.34", "10.0.0.5", "10.0.0.5"])
    monkeypatch.setattr(
        page_reader_module.socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(answers), port))
        ],
    )
    seen: list[tuple[str, int | None, str, object]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(
            (req.url.host, req.url.port, req.headers["host"], req.extensions.get("sni_hostname"))
        )
        return _site(req)

    text = await HttpArticlePageReader(transport=httpx.MockTransport(handler)).read(
        "https://pub.example/ok?a=1"
    )
    assert text.startswith("본문 문장입니다.")
    assert seen == [
        ("93.184.216.34", None, "pub.example", "pub.example")
    ]  # 443은 기본 포트라 생략됨


@pytest.mark.asyncio
async def test_page_reader_bad_redirect_location_gives_empty(fake_dns):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": req.url.params["to"]})

    reader = HttpArticlePageReader(transport=httpx.MockTransport(handler))
    for bad in ("http://pub.example:bad/x", "http://[bad/x"):
        assert await reader.read(f"https://pub.example/start?to={bad}") == ""


class _EndlessPage(httpx.AsyncByteStream):
    """끝없이 보내는 페이지 — 읽은 양을 센다(10MB에서 멈춰 테스트가 매달리지 않게)."""

    def __init__(self) -> None:
        self.sent = 0

    async def __aiter__(self):
        yield b"<article><p>"
        while self.sent < 10_000_000:
            self.sent += 65_536
            yield "가".encode() * 21_845 + b"a"


@pytest.mark.asyncio
async def test_page_reader_stops_reading_at_size_limit(fake_dns):
    page = _EndlessPage()
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, headers={"content-type": "text/html"}, stream=page)
    )
    text = await HttpArticlePageReader(transport=transport).read("https://pub.example/huge")
    assert 0 < len(text) <= page_reader_module.MAX_CHARS
    assert page.sent <= page_reader_module.MAX_BYTES + 65_536


@pytest.mark.asyncio
async def test_page_reader_skips_compressed_responses(fake_dns):
    asked: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        asked.append(req.headers["accept-encoding"])
        body = gzip.compress(("<article><p>" + "본문 문장입니다. " * 5).encode())
        headers = {"content-type": "text/html", "content-encoding": "gzip"}
        return httpx.Response(200, headers=headers, content=body)

    reader = HttpArticlePageReader(transport=httpx.MockTransport(handler))
    assert await reader.read("https://pub.example/gz") == ""
    assert asked == ["identity"]


class _TricklePage(httpx.AsyncByteStream):
    """읽기 시간 제한보다 짧은 간격으로 조금씩 끝없이 보낸다."""

    async def __aiter__(self):
        yield b"<article><p>"
        while True:
            await asyncio.sleep(0.01)
            yield b"a"


@pytest.mark.asyncio
async def test_page_reader_gives_up_after_total_timeout(fake_dns, monkeypatch):
    monkeypatch.setattr(page_reader_module, "TOTAL_TIMEOUT_S", 0.3)
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200, headers={"content-type": "text/html"}, stream=_TricklePage()
        )
    )
    started = time.monotonic()
    reader = HttpArticlePageReader(transport=transport)
    # 상한이 없으면 끝나지 않으니 테스트가 매달리지 않게 바깥에서 5초로 끊는다
    assert await asyncio.wait_for(reader.read("https://pub.example/slow"), 5) == ""
    assert time.monotonic() - started < 2


@pytest.mark.asyncio
async def test_page_reader_odd_charset_gives_empty_not_error(fake_dns):
    headers = {"content-type": "text/html; charset=base64_codec"}
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, headers=headers, content=b"<article><p>!!not base64!!")
    )
    assert await HttpArticlePageReader(transport=transport).read("https://pub.example/odd") == ""
