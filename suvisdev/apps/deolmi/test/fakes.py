"""출력 포트 fake — 포트 ABC를 실제로 상속해 인터페이스가 바뀌면 테스트가 먼저 깨진다."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import redis

from deolmi.app.dtos.score_dto import ScoreResultDto
from deolmi.app.dtos.site_dto import EventSummaryDto, SiteCreateCommand, SiteDto
from deolmi.app.ports.output.anomaly_model_port import AnomalyModelPort
from deolmi.app.ports.output.event_repository import EventRepositoryPort
from deolmi.app.ports.output.site_repository import SiteRepositoryPort
from deolmi.app.ports.output.velocity_port import VelocityPort
from deolmi.domain.services.site_keys import hash_secret

HUMAN = {
    "move_count": 130,
    "path_px": 2600,
    "straightness": 0.5,
    "click_count": 3,
    "click_iv_mean": 850,
    "click_iv_std": 260,
    "key_count": 12,
    "key_iv_std": 95,
    "dwell_ms": 6500,
}
BOT = {**HUMAN, "key_iv_std": 0, "click_iv_std": 0, "straightness": 1.0}
# 휴대폰: 마우스 없음, 터치 스크롤·탭. 키보드: 마우스를 안 쓰고 Tab·Enter로 제출.
TOUCH_HUMAN = {
    **HUMAN,
    "move_count": 0,
    "path_px": 0,
    "straightness": 0,
    "touch_count": 40,
}
KEYBOARD_HUMAN = {
    **HUMAN,
    "move_count": 0,
    "path_px": 0,
    "straightness": 0,
    "click_count": 1,
    "click_iv_mean": 0,
    "click_iv_std": 0,
    "kbd_click_count": 1,
}


def make_site(
    site_key: str = "pk_test", secret: str = "sk_test", domains: tuple[str, ...] = ()
) -> SiteDto:
    return SiteDto(
        id=1,
        site_key=site_key,
        secret_hash=hash_secret(secret),
        name="test",
        plan="free",
        domains=domains,
        active=True,
        created_at=datetime(2026, 10, 20),
    )


class _FakeSiteRepository(SiteRepositoryPort):
    def __init__(self, *sites: SiteDto) -> None:
        self.sites = {s.site_key: s for s in sites}

    async def get_active(self, site_key: str) -> SiteDto | None:
        return self.sites.get(site_key)

    async def create(self, command: SiteCreateCommand, site_key: str, secret_hash: str) -> SiteDto:
        site = SiteDto(
            id=len(self.sites) + 1,
            site_key=site_key,
            secret_hash=secret_hash,
            name=command.name,
            plan=command.plan,
            domains=command.domains,
            active=True,
            created_at=datetime(2026, 10, 20),
        )
        self.sites[site_key] = site
        return site

    async def list_all(self) -> list[SiteDto]:
        return list(self.sites.values())


class _FakeEventRepository(EventRepositoryPort):
    def __init__(self, fail: bool = False) -> None:
        self.rows: list[tuple[int, str, dict[str, float], ScoreResultDto]] = []
        self.fail = fail

    async def add(
        self, site_id: int, ip: str, signals: dict[str, float], result: ScoreResultDto
    ) -> None:
        if self.fail:
            raise RuntimeError("db down")
        self.rows.append((site_id, ip, signals, result))

    async def count(self) -> int:
        return len(self.rows)

    async def recent(self, n: int) -> list[EventSummaryDto]:
        return []

    async def signals_by_verdict(self, verdict: str, limit: int) -> list[dict[str, Any]]:
        return [r[2] for r in self.rows if r[3].verdict == verdict][:limit]


class _FakeModel(AnomalyModelPort):
    def __init__(self, value: float = 0.2) -> None:
        self.value = value
        self.calls = 0

    @property
    def source(self) -> str:
        return "fake"

    def score(self, features: list[float]) -> float:
        self.calls += 1
        return self.value


class _FakeVelocity(VelocityPort):
    def __init__(self, count: int = 1) -> None:
        self.count = count
        self.keys: list[str] = []

    def record(self, key: str) -> int:
        self.keys.append(key)
        return self.count


class _FakeRedis:
    """dict 기반 최소 Redis — deolmi가 쓰는 set(nx, ex)·incr·expire만. down이면 연결 오류."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttl: dict[str, int] = {}
        self.down = False

    def _check(self) -> None:
        if self.down:
            raise redis.ConnectionError("redis down")

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool | None:
        self._check()
        if nx and key in self.store:
            return None
        self.store[key] = value
        if ex is not None:
            self.ttl[key] = ex
        return True

    def incr(self, key: str) -> int:
        self._check()
        self.store[key] = str(int(self.store.get(key, "0")) + 1)
        return int(self.store[key])

    def expire(self, key: str, seconds: int) -> bool:
        self._check()
        self.ttl[key] = seconds
        return True
