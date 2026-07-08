from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformGroupsQuery:
    id: int
    name: str


@dataclass(frozen=True)
class PlatformGroupsResponse:
    id: int
    name: str
