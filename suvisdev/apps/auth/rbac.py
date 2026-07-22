from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """auth 게이트웨이 전용 역할 정의.

    viewer.app.dtos.role.UserRole을 import하지 않고 독립적으로 정의한다 —
    auth-isolation import-linter 계약 방향과 맞추기 위한 의도적 중복.
    """

    ADMIN = "admin"
    USER = "user"


class Permission(StrEnum):
    VIEW_ADMIN_DASHBOARD = "view_admin_dashboard"
    MANAGE_USERS = "manage_users"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset({Permission.VIEW_ADMIN_DASHBOARD, Permission.MANAGE_USERS}),
    Role.USER: frozenset(),
}


def has_permission(roles: list[str], permission: Permission) -> bool:
    for raw in roles:
        try:
            role = Role(raw)
        except ValueError:
            continue
        if permission in ROLE_PERMISSIONS.get(role, frozenset()):
            return True
    return False
