from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PassengerCommand:
    """ERD Person — 승객 1명."""

    passenger_id: str
    name: str
    gender: str
    age: str
    sib_sp: str
    parch: str
    survived: str


@dataclass
class BookingCommand:
    """ERD Booking + Port 역정규화 (country 제외)."""

    pclass: str
    ticket: str
    fare: str
    cabin: str
    embarked: str


@dataclass
class JamesResponse:
    answer: str


@dataclass(frozen=True)
class JamesIntroduceQuery:
    id: int
    name: str


@dataclass(frozen=True)
class JamesIntroduceResponse:
    id: int
    name: str
