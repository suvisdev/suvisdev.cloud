"""테스트 전용 RateLimiterPort — 실제로 안 기다리고 호출만 기록한다."""

from __future__ import annotations

from ontology.app.ports.output.rate_limiter_port import RateLimiterPort


class FakeRateLimiter(RateLimiterPort):
    def __init__(self) -> None:
        self.acquired_domains: list[str] = []

    def acquire(self, domain: str) -> None:
        self.acquired_domains.append(domain)
