"""테스트 전용 PageFetcherPort — 실제 httpx 호출 없이 고정 응답을 돌려준다."""

from __future__ import annotations

from ontology.app.ports.output.page_fetcher_port import PageFetcherPort


class FakePageFetcher(PageFetcherPort):
    """url에 substring이 매칭되는 첫 규칙의 응답을 반환한다. 매칭 안 되면 KeyError."""

    def __init__(self, *, single_response: str | None = None) -> None:
        self._single_response = single_response
        self._rules: list[tuple[str, str]] = []
        self.fetched_urls: list[str] = []

    def add_rule(self, url_contains: str, response: str) -> None:
        self._rules.append((url_contains, response))

    def fetch(self, url: str) -> str:
        self.fetched_urls.append(url)
        if self._single_response is not None:
            return self._single_response
        for needle, response in self._rules:
            if needle in url:
                return response
        raise KeyError(f"매칭되는 fake 응답 규칙 없음: {url}")
