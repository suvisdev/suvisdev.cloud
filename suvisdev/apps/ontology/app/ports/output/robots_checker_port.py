from __future__ import annotations

from abc import ABC, abstractmethod


class RobotsCheckerPort(ABC):
    @abstractmethod
    def is_allowed(self, url: str) -> bool:
        """이 URL을 크롤링해도 되는지 robots.txt 기준으로 판단한다.

        robots.txt 자체를 못 읽으면(없음·타임아웃) fail-open으로 True를 반환한다.
        """
