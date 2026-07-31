from sqlalchemy import create_engine, inspect

from analytics.adapter.outbound.orm.visitor_activity_orm import VisitorActivityOrm
from core.matrix.grid_neo_theone_base import Base


def _create_all():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[VisitorActivityOrm.__table__])
    return engine


class TestOrmSchema:
    def test_visitor_activity_table_is_created(self):
        engine = _create_all()
        tables = set(inspect(engine).get_table_names())
        assert "visitor_activity" in tables

    def test_pk_is_visitor_id_and_visit_date(self):
        engine = _create_all()
        pk = inspect(engine).get_pk_constraint("visitor_activity")
        assert set(pk["constrained_columns"]) == {"visitor_id", "visit_date"}
