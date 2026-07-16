"""CustomUrlScrapeInteractor 테스트용 fake 모음."""

from __future__ import annotations

from ontology.app.dtos.custom_scrape_dto import ExtractedPage
from ontology.app.ports.output.page_extractor_port import PageExtractorPort
from ontology.app.ports.output.robots_checker_port import RobotsCheckerPort


class FakeRobotsChecker(RobotsCheckerPort):
    def __init__(self, *, allowed: bool = True) -> None:
        self._allowed = allowed
        self.checked_urls: list[str] = []

    def is_allowed(self, url: str) -> bool:
        self.checked_urls.append(url)
        return self._allowed


class FakePageExtractor(PageExtractorPort):
    def __init__(self, *, title: str = "가짜 제목", content: str = "가짜 추출 결과") -> None:
        self._title = title
        self._content = content
        self.received: list[tuple[str, str]] = []

    async def extract(self, html: str, instruction: str) -> ExtractedPage:
        self.received.append((html, instruction))
        return ExtractedPage(title=self._title, content=self._content)
