from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """auth 게이트웨이 전용 역할 정의.

    viewer.app.dtos.role.UserRole을 import하지 않고 독립적으로 정의한다 —
    auth-isolation import-linter 계약 방향과 맞추기 위한 의도적 중복.
    """

    ADMIN = "admin"
    USER = "user"
