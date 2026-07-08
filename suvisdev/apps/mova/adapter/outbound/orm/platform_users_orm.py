"""platform_users — viewer(Secom DB) 소유. Mova 에서는 user_id FK 로만 참조함."""

from mova.adapter.outbound.orm.base_orm import MovaModel


class PlatformUsersOrm(MovaModel):
    __abstract__ = True
