"""③ 시간 의존 그늘 · ④ 제약 최단경로 · ⑤ 루프 — 합성 격자 위에서 정책 검증.

합성 세계는 scripts/verify_pipeline_synthetic.build_world (3행×5열, 100m 간격,
1행 가로 간선 `벚꽃로`). 그늘은 해석적으로 준다(shapely 불필요).
"""

from __future__ import annotations

from tests.app.fakes import FakeHazardZoneRepository, FakeTreeSegmentRepository

from gildle.adapter.outbound.graph.dijkstra_route_graph_adapter import (
    AStarRouteGraphAdapter,
)
from gildle.app.use_cases.calculate_route_interactor import (
    CalculateDogFriendlyRouteInteractor,
    path_length_m,
)
from gildle.app.use_cases.plan_loop_interactor import PlanLoopRouteInteractor
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.season_mode import SeasonMode
from gildle.scripts.verify_pipeline_synthetic import (
    World,
    _node,
    analytic_noon_lookup,
    build_world,
)


def _route_interactor() -> CalculateDogFriendlyRouteInteractor:
    return CalculateDogFriendlyRouteInteractor(
        tree_repository=FakeTreeSegmentRepository(),
        hazard_repository=FakeHazardZoneRepository(),
        route_graph=AStarRouteGraphAdapter(),
        weight_calculator=RouteWeightCalculator(),
    )


def _loop_interactor() -> PlanLoopRouteInteractor:
    return PlanLoopRouteInteractor(
        tree_repository=FakeTreeSegmentRepository(),
        hazard_repository=FakeHazardZoneRepository(),
        route_graph=AStarRouteGraphAdapter(),
        weight_calculator=RouteWeightCalculator(),
    )


def _nearest(world: World):
    coords: dict[str, Coordinate] = {}
    for e in world.edges:
        if e.from_coord is not None:
            coords.setdefault(e.from_node, e.from_coord)
        if e.to_coord is not None:
            coords.setdefault(e.to_node, e.to_coord)

    def nearest(c: Coordinate) -> str | None:
        return min(coords, key=lambda n: coords[n].distance_to(c)) if coords else None

    return nearest


class TestBoundedDetour:
    """④ 여름 정오: 그늘 우회(600m)는 최단(400m)의 1.5배 — 상한 0.3이면 직행, 0.5면 우회."""

    def test_tight_bound_keeps_shortest(self):
        world = build_world()
        path = _route_interactor().execute_bounded(
            world.edges,
            _node(0, 0),
            _node(0, 4),
            SeasonMode.SUMMER_SHADE,
            shade_lookup=analytic_noon_lookup(world),
            max_detour_ratio=0.3,
        )
        assert abs(path_length_m(world.edges, path) - 400.0) < 1e-6

    def test_loose_bound_allows_shaded_detour(self):
        world = build_world()
        path = _route_interactor().execute_bounded(
            world.edges,
            _node(0, 0),
            _node(0, 4),
            SeasonMode.SUMMER_SHADE,
            shade_lookup=analytic_noon_lookup(world),
            max_detour_ratio=0.5,
        )
        assert abs(path_length_m(world.edges, path) - 600.0) < 1e-6

    def test_never_exceeds_limit_across_ratios(self):
        world = build_world()
        shortest = 400.0
        for ratio in (0.0, 0.1, 0.25, 0.49, 0.5, 1.0, 2.0):
            path = _route_interactor().execute_bounded(
                world.edges,
                _node(0, 0),
                _node(0, 4),
                SeasonMode.SUMMER_SHADE,
                shade_lookup=analytic_noon_lookup(world),
                max_detour_ratio=ratio,
            )
            assert path_length_m(world.edges, path) <= shortest * (1 + ratio) + 1e-6, ratio


class TestTimeAwareShade:
    """③ 출발 슬롯엔 직행(0행)이 그늘, 200m 걸은 뒤 슬롯에선 0행만 햇빛이고 나머지가 그늘.
    고정 슬롯이면 직행을 고르고, 시간 의존이면 도중에 0행을 벗어나야 한다."""

    def test_uses_slot_of_arrival(self):
        world = build_world()

        def row0_only(shaded: bool) -> dict[tuple[str, str], float]:
            out = {}
            for e in world.edges:
                on_row0 = e.from_node[1] == "0" and e.to_node[1] == "0"
                out[(e.from_node, e.to_node)] = (
                    (1.0 if on_row0 else 0.0) if shaded else (0.0 if on_row0 else 1.0)
                )
            return out

        by_slot = {12: row0_only(True), 13: row0_only(False)}
        interactor = _route_interactor()
        time_aware = interactor.execute_time_aware(
            world.edges,
            _node(0, 0),
            _node(0, 4),
            SeasonMode.SUMMER_SHADE,
            shade_by_slot=by_slot,
            slot_of_elapsed=lambda m: 12 if m < 200 else 13,
        )
        fixed = interactor.execute(
            world.edges, _node(0, 0), _node(0, 4), SeasonMode.SUMMER_SHADE, shade_lookup=by_slot[12]
        )
        assert all(n.startswith("n0_") for n in fixed), fixed
        assert any(not n.startswith("n0_") for n in time_aware), time_aware
        assert time_aware[0] == _node(0, 0) and time_aware[-1] == _node(0, 4)


class TestLoopPlanning:
    """⑤ 출발=도착, 목표 거리 근처, 되밟기 적음."""

    def test_returns_closed_loops_near_target(self):
        world = build_world()
        loops = _loop_interactor().execute(
            world.edges,
            _node(1, 2),
            600.0,
            SeasonMode.SPRING_AUTUMN,
            nearest_node=_nearest(world),
            limit=3,
        )
        assert loops, "루프 후보 없음"
        for loop in loops:
            assert loop.path[0] == loop.path[-1] == _node(1, 2)
            assert abs(loop.length_m - 600.0) <= 0.35 * 600.0
            assert loop.overlap_ratio <= 0.5

    def test_summer_prefers_shaded_loop(self):
        world = build_world()
        loops = _loop_interactor().execute(
            world.edges,
            _node(1, 2),
            600.0,
            SeasonMode.SUMMER_SHADE,
            nearest_node=_nearest(world),
            shade_lookup=analytic_noon_lookup(world),
            limit=3,
        )
        assert loops
        assert loops[0].shade_ratio is not None and loops[0].shade_ratio > 0.0
