"""회원 프로필 코드값 — `users` 테이블 컬럼."""

from enum import StrEnum


class UserGender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNDISCLOSED = "undisclosed"


class UserAgeGroup(StrEnum):
    TEENS = "10s"
    TWENTIES = "20s"
    THIRTIES = "30s"
    FORTIES = "40s"
    FIFTIES = "50s"
    SIXTIES_PLUS = "60s_plus"
    UNDISCLOSED = "undisclosed"


USER_GENDERS = frozenset({g.value for g in UserGender})
USER_AGE_GROUPS = frozenset({a.value for a in UserAgeGroup})
