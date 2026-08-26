"""회원 프로필 코드값 — `users` 테이블 컬럼."""

from enum import StrEnum


class UserGender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNDISCLOSED = "undisclosed"


USER_GENDERS = frozenset({g.value for g in UserGender})
