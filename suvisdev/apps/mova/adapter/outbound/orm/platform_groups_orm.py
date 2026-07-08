"""platform_groups — viewer(Secom DB) 소유. Mova 에서는 FK 참조만 함."""

from mova.adapter.outbound.orm.base_orm import MovaModel


class PlatformGroupsOrm(MovaModel):
    __abstract__ = True
