"""합성 데이터로 경로 파이프라인을 끝까지 돌리는 검증 하네스.

실데이터(23만 간선·80만 동)로는 "이 경로가 맞는가"를 판정할 정답이 없다. 대신
정답을 **아는** 작은 세계를 만든다 — 격자 도로 3행×5열(간격 100m), 특정 거리
남쪽에만 40m 건물을 세우면 정오에는 그 거리만 그늘이어야 하고, 여름 모드는
400m 직행 대신 그 거리로 돌아가야 한다. 각 모드가 규칙대로 움직이는지를
태양 위치 → 그림자 → 간선 그늘 → 가중치 → 최단경로 순서 그대로 검사한다.

    python -m gildle.scripts.verify_pipeline_synthetic        # 사람용 출력 + JSON 요약
    pytest apps/gildle/tests/scripts/test_verify_pipeline_synthetic.py

shapely가 없는 환경(서빙 이미지)에서는 그림자 기하 케이스만 건너뛰고, 경로
규칙 케이스는 해석적으로 만든 그늘 lookup으로 계속 돈다.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from gildle.adapter.outbound.graph.networkx_route_graph_adapter import (
    NetworkXRouteGraphAdapter,
)
from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.app.use_cases.calculate_route_interactor import (
    CalculateDogFriendlyRouteInteractor,
)
from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.services.sun_position import sun_altitude_azimuth
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode
from gildle.domain.value_objects.tree_species import TreeSpecies

try:
    from gildle.scripts.compute_shade_scores import compute_slot_fractions

    HAS_SHAPELY = True
except ImportError:  # 서빙 이미지에는 shapely가 없다
    HAS_SHAPELY = False

_LAT0, _LNG0 = 37.5665, 126.9780  # compute_shade_scores._SEOUL_CENTER와 같은 원점
_KST = timezone(timedelta(hours=9))
_ROWS, _COLS, _SPACING_M = 3, 5, 100.0
_BUILDING_H_M = 40.0
_BONUS_ROAD = "벚꽃로"


# ── 합성 세계 ────────────────────────────────────────────────────────────────


def _to_latlng(x_m: float, y_m: float) -> tuple[float, float]:
    """project_to_meters의 역변환(등장방형 근사)."""
    return _LAT0 + y_m / 110540.0, _LNG0 + x_m / (111320.0 * math.cos(math.radians(_LAT0)))


def _node(r: int, c: int) -> str:
    return f"n{r}_{c}"


@dataclass(frozen=True)
class World:
    edges: list[RouteEdge]
    raw_edges: list[dict[str, Any]]  # compute_slot_fractions 입력 형식
    buildings: list[dict[str, Any]]


def build_world() -> World:
    """3행×5열 격자. 1행 거리 남쪽(y 70~95m)에 40m 건물 → 정오에 1행만 그늘.
    4열 세로 거리 동쪽(x 405~430m)에 40m 건물 → 오전에만 그 세로 거리가 그늘.
    1행 가로 간선은 `벚꽃로`(봄 보너스 수종 매칭용)."""
    edges: list[RouteEdge] = []
    raw: list[dict[str, Any]] = []

    def add(r1: int, c1: int, r2: int, c2: int) -> None:
        x1, y1 = c1 * _SPACING_M, r1 * _SPACING_M
        x2, y2 = c2 * _SPACING_M, r2 * _SPACING_M
        lat1, lng1 = _to_latlng(x1, y1)
        lat2, lng2 = _to_latlng(x2, y2)
        road = _BONUS_ROAD if (r1 == r2 == 1) else None
        edges.append(
            RouteEdge(
                from_node=_node(r1, c1),
                to_node=_node(r2, c2),
                base_distance_m=_SPACING_M,
                midpoint=Coordinate(latitude=(lat1 + lat2) / 2, longitude=(lng1 + lng2) / 2),
                road_name=road,
                from_coord=Coordinate(latitude=lat1, longitude=lng1),
                to_coord=Coordinate(latitude=lat2, longitude=lng2),
            )
        )
        raw.append(
            {
                "from_node": _node(r1, c1),
                "to_node": _node(r2, c2),
                "from_lat": lat1,
                "from_lng": lng1,
                "to_lat": lat2,
                "to_lng": lng2,
                "tree_score": 0.0,
            }
        )

    for r in range(_ROWS):
        for c in range(_COLS - 1):
            add(r, c, r, c + 1)
    for r in range(_ROWS - 1):
        for c in range(_COLS):
            add(r, c, r + 1, c)

    def box(x1: float, y1: float, x2: float, y2: float) -> dict[str, Any]:
        pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        return {
            "outline": [list(_to_latlng(x, y)) for x, y in pts],
            "height_m": _BUILDING_H_M,
            "height_known": True,
        }

    buildings = [box(-20.0, 70.0, 420.0, 95.0), box(405.0, 105.0, 430.0, 195.0)]
    return World(edges=edges, raw_edges=raw, buildings=buildings)


def _shade_lookup_from_fractions(frac: Mapping[str, int]) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for key, pct in frac.items():
        a, _, b = key.partition("-")
        out[(a, b)] = pct / 100.0
    return out


def analytic_noon_lookup(world: World) -> dict[tuple[str, str], float]:
    """shapely 없이도 경로 규칙을 검사하기 위한 정오 그늘(1행 가로 간선만 1.0)."""
    return {
        (e.from_node, e.to_node): (1.0 if e.road_name == _BONUS_ROAD else 0.0) for e in world.edges
    }


# ── 최소 포트 구현(테스트 패키지에 의존하지 않기 위해 스크립트 안에 둔다) ──


class _Trees(TreeSegmentRepository):
    def __init__(self, segments: list[TreeSegment]) -> None:
        self._s = segments

    def find_all(self) -> list[TreeSegment]:
        return list(self._s)

    def save_many(self, segments: list[TreeSegment]) -> None:
        self._s.extend(segments)


class _Hazards(HazardZoneRepository):
    def __init__(self, hazards: list[HazardZone]) -> None:
        self._h = hazards

    def find_all(self) -> list[HazardZone]:
        return list(self._h)


def _interactor(
    trees: list[TreeSegment] | None = None, hazards: list[HazardZone] | None = None
) -> CalculateDogFriendlyRouteInteractor:
    return CalculateDogFriendlyRouteInteractor(
        tree_repository=_Trees(trees or []),
        hazard_repository=_Hazards(hazards or []),
        route_graph=NetworkXRouteGraphAdapter(),
        weight_calculator=RouteWeightCalculator(),
    )


# ── 검사 도구 ────────────────────────────────────────────────────────────────


def _edge_map(world: World) -> dict[tuple[str, str], RouteEdge]:
    m: dict[tuple[str, str], RouteEdge] = {}
    for e in world.edges:
        m[(e.from_node, e.to_node)] = e
        m[(e.to_node, e.from_node)] = e
    return m


def _walk(world: World, path: list[str]) -> list[RouteEdge]:
    m = _edge_map(world)
    return [m[(path[i], path[i + 1])] for i in range(len(path) - 1)]


def _length(world: World, path: list[str]) -> float:
    return sum(e.base_distance_m for e in _walk(world, path))


def _shade_ratio(world: World, path: list[str], lookup: Mapping[tuple[str, str], float]) -> float:
    total = shaded = 0.0
    for e in _walk(world, path):
        s = lookup.get((e.from_node, e.to_node))
        if s is None:
            s = lookup.get((e.to_node, e.from_node), 0.0)
        total += e.base_distance_m
        shaded += e.base_distance_m * s
    return shaded / total if total else 0.0


def _connected(world: World, path: list[str], start: str, end: str) -> bool:
    if not path or path[0] != start or path[-1] != end:
        return False
    m = _edge_map(world)
    return all((path[i], path[i + 1]) in m for i in range(len(path) - 1))


@dataclass
class Case:
    name: str
    passed: bool
    detail: str
    skipped: bool = False


# ── 케이스 ───────────────────────────────────────────────────────────────────


def run_cases(date: datetime | None = None) -> list[Case]:
    world = build_world()
    day = date or datetime(2026, 8, 1, tzinfo=_KST)
    cases: list[Case] = []
    start, end = _node(0, 0), _node(0, 4)  # 남서 → 남동, 직행 400m

    # 1) 태양 → 그림자 → 간선 그늘 (기하) ---------------------------------
    lookups: dict[int, dict[tuple[str, str], float]] = {}
    if HAS_SHAPELY:
        for slot in (9, 12, 15):
            alt, az = sun_altitude_azimuth(_LAT0, _LNG0, day.replace(hour=slot, minute=0))
            frac = compute_slot_fractions(world.raw_edges, world.buildings, alt, az)
            lookups[slot] = _shade_lookup_from_fractions(frac)
        noon = lookups[12]
        row1 = [noon[(_node(1, c), _node(1, c + 1))] for c in range(_COLS - 1)]
        row0 = [noon[(_node(0, c), _node(0, c + 1))] for c in range(_COLS - 1)]
        cases.append(
            Case(
                "정오: 건물 북쪽 거리(1행)만 그늘",
                min(row1) >= 0.9 and max(row0) == 0.0,
                f"1행 {[round(v, 2) for v in row1]} · 0행 {[round(v, 2) for v in row0]}",
            )
        )
        vert = (_node(1, 4), _node(2, 4))
        am, pm = lookups[9][vert], lookups[15][vert]
        cases.append(
            Case(
                "동쪽 건물이 있는 세로 거리: 오전 그늘 > 오후 그늘",
                am > 0.5 > pm,
                f"09시 {am:.2f} · 15시 {pm:.2f}",
            )
        )
    else:
        cases.append(Case("그림자 기하(shapely 필요)", True, "shapely 없음 — 건너뜀", skipped=True))
        lookups[12] = analytic_noon_lookup(world)
    noon = lookups[12]

    # 2) 여름 그늘 모드: 400m 직행 대신 그늘 거리로 우회 --------------------
    path = _interactor().execute(
        world.edges, start, end, SeasonMode.SUMMER_SHADE, shade_lookup=noon
    )
    straight = _interactor().execute(world.edges, start, end, SeasonMode.SPRING_AUTUMN)
    ok = (
        _connected(world, path, start, end)
        and _shade_ratio(world, path, noon) > _shade_ratio(world, straight, noon)
        and _length(world, path) <= 600.0 + 1e-6
    )
    cases.append(
        Case(
            "여름 정오: 그늘 거리로 우회(길이 ≤600m, 그늘비율 ↑)",
            ok,
            f"길이 {_length(world, path):.0f}m 그늘 {_shade_ratio(world, path, noon):.2f} "
            f"vs 직행 {_length(world, straight):.0f}m 그늘 {_shade_ratio(world, straight, noon):.2f}",
        )
    )

    # 3) 밤(모든 간선 그늘 1.0): 순수 최단 --------------------------------
    class _AllShade(dict[tuple[str, str], float]):
        def get(self, key: Any, default: Any = None) -> float:
            return 1.0

    night = _interactor().execute(
        world.edges, start, end, SeasonMode.SUMMER_SHADE, shade_lookup=_AllShade()
    )
    cases.append(
        Case(
            "밤: 그늘 무의미 → 최단 400m",
            _connected(world, night, start, end) and abs(_length(world, night) - 400.0) < 1e-6,
            f"길이 {_length(world, night):.0f}m",
        )
    )

    # 4) 겨울: 직행 위 결빙 위험구역 회피 ----------------------------------
    mid = _edge_map(world)[(_node(0, 2), _node(0, 3))].midpoint
    hazard = HazardZone(id=1, center=mid, radius_meters=200.0, accident_count=3, description="결빙")
    winter = _interactor(hazards=[hazard]).execute(
        world.edges, start, end, SeasonMode.WINTER_SAFETY
    )
    cases.append(
        Case(
            "겨울: 위험구역 간선 회피",
            _connected(world, winter, start, end)
            and all(e.midpoint.distance_to(mid) > 20.0 for e in _walk(world, winter)),
            f"경로 {'→'.join(winter)}",
        )
    )

    # 5) 봄: 동일 길이 후보 중 보너스 수종 거리 선호 -----------------------
    seg = TreeSegment(
        id=1,
        road_name=_BONUS_ROAD,
        start=Coordinate(*_to_latlng(0.0, 100.0)),
        end=Coordinate(*_to_latlng(400.0, 100.0)),
        species=TreeSpecies.CHERRY,
        quantity=50,
        managing_agency="합성",
    )
    s2, e2 = _node(0, 0), _node(2, 4)  # 모든 맨해튼 경로가 600m — 보너스로만 갈린다
    spring = _interactor(trees=[seg]).execute(world.edges, s2, e2, SeasonMode.SPRING_AUTUMN)
    horiz = [e for e in _walk(world, spring) if e.from_node[1] == e.to_node[1]]
    cases.append(
        Case(
            "봄: 같은 길이면 벚꽃로(보너스 수종) 선택",
            _connected(world, spring, s2, e2)
            and len(horiz) == _COLS - 1
            and all(e.road_name == _BONUS_ROAD for e in horiz),
            f"가로 간선 도로명 {[e.road_name for e in horiz]}",
        )
    )

    # 6) 불변식: 가중치 최적 경로의 비용 ≤ 최단거리 경로의 비용 ----------
    calc = RouteWeightCalculator()

    def cost(p: list[str]) -> float:
        return sum(
            calc.calculate_edge_weight(
                e,
                SeasonMode.SUMMER_SHADE,
                [],
                [],
                shade_fraction=noon.get((e.from_node, e.to_node)),
            ).value
            for e in _walk(world, p)
        )

    cases.append(
        Case(
            "불변식: 선택 경로 비용 ≤ 최단거리 경로 비용",
            cost(path) <= cost(straight) + 1e-6,
            f"{cost(path):.0f} ≤ {cost(straight):.0f}",
        )
    )
    return cases


def main() -> None:
    cases = run_cases()
    for i, c in enumerate(cases, 1):
        tag = "SKIP" if c.skipped else ("PASS" if c.passed else "FAIL")
        print(f"[{i}/{len(cases)}] {tag} | {c.name} | {c.detail}")
    passed = sum(1 for c in cases if c.passed and not c.skipped)
    total = sum(1 for c in cases if not c.skipped)
    print(
        f"\n결과: {passed}/{total} PASS"
        + (" (shapely 없음: 기하 케이스 제외)" if not HAS_SHAPELY else "")
    )
    print(json.dumps({"passed": passed, "total": total, "shapely": HAS_SHAPELY}))


if __name__ == "__main__":
    main()
