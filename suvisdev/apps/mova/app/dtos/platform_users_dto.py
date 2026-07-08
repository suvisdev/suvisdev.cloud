from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformUsersQuery:
    id: int
    name: str


@dataclass(frozen=True)
class PlatformUsersResponse:
    id: int
    name: str
