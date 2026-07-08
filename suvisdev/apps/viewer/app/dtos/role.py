from enum import StrEnum


class UserRole(StrEnum):
    """그룹 코드 — `groups.code` 값 (admin / user)."""

    ADMIN = "admin"
    USER = "user"
