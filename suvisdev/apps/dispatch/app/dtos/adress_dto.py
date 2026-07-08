from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdressCommand:
    first_name: str
    middle_name: str
    last_name: str
    phonetic_first_name: str
    phonetic_middle_name: str
    phonetic_last_name: str
    name_prefix: str
    name_suffix: str
    nickname: str
    file_as: str
    organization_name: str
    organization_title: str
    organization_department: str
    birthday: str
    notes: str
    photo: str
    labels: str
    email_label: str
    email: str


@dataclass
class AdressResponse:
    row_count: int


@dataclass
class AdressIntroduceQuery:
    id: int
    name: str


@dataclass
class AdressIntroduceResponse:
    id: int
    name: str


@dataclass(frozen=True)
class AdressSearchQuery:
    q: str


@dataclass(frozen=True)
class AdressSearchResult:
    name: str
    email: str
