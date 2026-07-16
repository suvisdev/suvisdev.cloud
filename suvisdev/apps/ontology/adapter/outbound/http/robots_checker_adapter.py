"""robots.txt 확인 — RobotsCheckerPort 구현체.

kinolights 건(User-Agent: * → Disallow: /)에서 배운 대로, 임의 URL을 지원하는
기능이라면 robots.txt 확인은 선택이 아니라 필수다. robots.txt 자체를 못 읽으면
(404·타임아웃 등) fail-open — 대부분의 사이트가 robots.txt가 없거나 접근이
느슨한 것뿐이지 그게 곧 "전부 허용"의 반대는 아니기 때문이다.
"""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from ontology.app.ports.output.crawl_errors import CrawlFetchError
from ontology.app.ports.output.page_fetcher_port import PageFetcherPort
from ontology.app.ports.output.robots_checker_port import RobotsCheckerPort

_USER_AGENT = "SuvisdevOntologyHarvester/1.0"


class HttpxRobotsCheckerAdapter(RobotsCheckerPort):
    def __init__(self, *, fetcher: PageFetcherPort) -> None:
        self._fetcher = fetcher

    def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            robots_txt = self._fetcher.fetch(robots_url)
        except CrawlFetchError:
            return True

        parser = RobotFileParser()
        parser.parse(robots_txt.splitlines())
        return parser.can_fetch(_USER_AGENT, url)
