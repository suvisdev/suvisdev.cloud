from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from deolmi.adapter.inbound.api.schemas.site_schema import (
        EventSummarySchema,
        SiteCreateSchema,
        SiteIssuedSchema,
        SiteSchema,
        StatsSchema,
    )


@dataclass(frozen=True)
class SiteCreateCommand:
    name: str
    plan: str
    domains: tuple[str, ...]

    @classmethod
    def from_schema(cls, schema: SiteCreateSchema) -> SiteCreateCommand:
        return cls(
            name=schema.name.strip(),
            plan=schema.plan,
            domains=tuple(d.strip().lower() for d in schema.domains if d.strip()),
        )


@dataclass(frozen=True)
class SiteDto:
    id: int
    site_key: str
    secret_hash: str  # 응답 스키마로 나가지 않는다(to_schema에서 뺀다)
    name: str
    plan: str
    domains: tuple[str, ...]
    active: bool
    created_at: datetime

    @classmethod
    def from_orm(cls, row: Any) -> SiteDto:
        return cls(
            id=row.id,
            site_key=row.site_key,
            secret_hash=row.secret_hash,
            name=row.name,
            plan=row.plan,
            domains=tuple(d for d in row.domains.split(",") if d),
            active=row.active,
            created_at=row.created_at,
        )

    def to_schema(self) -> SiteSchema:
        from deolmi.adapter.inbound.api.schemas.site_schema import SiteSchema

        return SiteSchema(
            site_key=self.site_key,
            name=self.name,
            plan=self.plan,
            domains=list(self.domains),
            active=self.active,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class IssuedSiteDto:
    site: SiteDto
    secret_key: str  # 이 응답에서 한 번만 보여 준다

    def to_schema(self) -> SiteIssuedSchema:
        from deolmi.adapter.inbound.api.schemas.site_schema import SiteIssuedSchema

        return SiteIssuedSchema(**self.site.to_schema().model_dump(), secret_key=self.secret_key)


@dataclass(frozen=True)
class EventSummaryDto:
    created_at: datetime
    site_key: str
    ip: str | None
    score: float
    verdict: str
    decided_by: str

    def to_schema(self) -> EventSummarySchema:
        from deolmi.adapter.inbound.api.schemas.site_schema import EventSummarySchema

        return EventSummarySchema(
            created_at=self.created_at,
            site_key=self.site_key,
            ip=self.ip,
            score=self.score,
            verdict=self.verdict,
            decided_by=self.decided_by,
        )


@dataclass(frozen=True)
class StatsDto:
    event_count: int
    model_source: str  # 'bootstrap'(가짜 표본) 또는 'trained(n=..)'(실데이터 재학습)
    recent: list[EventSummaryDto]

    def to_schema(self) -> StatsSchema:
        from deolmi.adapter.inbound.api.schemas.site_schema import StatsSchema

        return StatsSchema(
            event_count=self.event_count,
            model_source=self.model_source,
            recent=[e.to_schema() for e in self.recent],
        )
