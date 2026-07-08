from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformAdminsQuery:
    id: int
    name: str


@dataclass(frozen=True)
class PlatformAdminsResponse:
    id: int
    name: str
