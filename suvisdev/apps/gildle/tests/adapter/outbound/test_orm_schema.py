from sqlalchemy import create_engine, inspect

# create_all이 동작하려면 모든 ORM 모듈이 import되어 metadata에 등록돼야 한다.
import gildle.adapter.outbound.orm.hazard_zone_orm  # noqa: F401
import gildle.adapter.outbound.orm.route_edge_orm  # noqa: F401
import gildle.adapter.outbound.orm.route_node_orm  # noqa: F401
import gildle.adapter.outbound.orm.tree_segment_orm  # noqa: F401
import gildle.adapter.outbound.orm.walk_orm  # noqa: F401
from gildle.adapter.outbound.orm.base import GildleBase


def _create_all():
    engine = create_engine("sqlite:///:memory:")
    GildleBase.metadata.create_all(engine)
    return engine


class TestOrmSchema:
    def test_all_tables_are_created(self):
        engine = _create_all()
        tables = set(inspect(engine).get_table_names())
        assert {
            "tree_segments",
            "hazard_zones",
            "walks",
            "route_nodes",
            "route_edges",
        } <= tables

    def test_route_edges_has_two_self_ref_fks_to_route_nodes(self):
        engine = _create_all()
        fks = inspect(engine).get_foreign_keys("route_edges")
        referred = [fk["referred_table"] for fk in fks]
        assert referred.count("route_nodes") == 2

    def test_tree_segments_pk_is_id(self):
        engine = _create_all()
        pk = inspect(engine).get_pk_constraint("tree_segments")
        assert pk["constrained_columns"] == ["id"]
