"""경로 후보 — 빠른 길 · 그늘 많은 길 · 푸른 길을 나란히 계산하고 고를 이유를 붙인다(2026-09-28).

사용자 요청: "이쪽으로 갈 땐 이런 좋은 점, 저쪽으로 갈 땐 이런 좋은 점 — 둘 중 골라서 산책". 경로를
고르는 건 모델이 아니라 그래프 탐색이다. 후보마다 다른 가중치(거리·그늘·수관)로 A*를 돌리고, 길이는
최단거리의 1.5배를 넘지 않게 묶는다. 이유 문장은 계산한 수치로만 만든다(route_option_describer).
경로 곁 50~150m의 동물병원·펫샵·용품점·애견카페를 함께 붙이고, 고르면 들렀다 가는 경로를 만든다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import replace

from gildle.app.dtos.route_option_dto import RouteOptionDto
from gildle.app.ports.input.calculate_route_use_case import CalculateDogFriendlyRouteUseCase
from gildle.app.ports.input.plan_loop_use_case import PlanLoopRouteUseCase
from gildle.app.ports.input.route_options_use_case import RouteOptionsUseCase
from gildle.app.ports.output.pet_place_port import PetPlacePort
from gildle.domain.services.route_geometry import (
    EdgeLookup,
    nearest_vertex,
    path_coordinates,
    path_edges,
)
from gildle.domain.services.route_option_describer import RouteOptionMetrics, describe
from gildle.domain.services.walk_preference import (
    Elevation,
    climb_m,
    combined_label,
    make_combined_weight,
    make_weight,
)
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.pet_place import PetPlace
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode

logger = logging.getLogger(__name__)

MAX_DETOUR_RATIO = 0.5  # 후보 길이 상한: 최단거리 × 1.5
SIMILAR_JACCARD = 0.8  # 간선 겹침이 이 이상이면 같은 길로 보고 뺀다
PLACE_NEAR_M = 150.0  # 경로 꼭짓점에서 이 거리 안의 장소만 "가는 길에"
MAX_PLACES = 6


def _edge_key(e: RouteEdge) -> tuple[str, str]:
    return (e.from_node, e.to_node) if e.from_node < e.to_node else (e.to_node, e.from_node)


class RouteOptionsInteractor(RouteOptionsUseCase):
    def __init__(
        self,
        route: CalculateDogFriendlyRouteUseCase,
        places: PetPlacePort,
        loops: PlanLoopRouteUseCase | None = None,
    ) -> None:
        self._route = route
        self._places = places
        self._loops = loops

    # --- 후보 계산 -------------------------------------------------------------------------

    def _path_for(
        self,
        kind: str,
        edges: list[RouteEdge],
        start: str,
        end: str,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        elevation: Elevation | None = None,
    ) -> list[str]:
        """선호(walk_preference)별 가중치로 최단거리 × 1.5 안에서 A*.

        빠른 길도 순수 거리가 아니라 차도 중심선 페널티(road_penalty)를 곱한 가중치로 찾는다
        (2026-10-01) — 강남대로 차도 한가운데를 "최단"이라고 그리던 것을 보도로 보낸다."""
        if kind == "via":
            kind = "fast"
        weight, floor = make_weight(kind, shade_lookup=shade_lookup, elevation=elevation)
        return self._route.execute_weighted(
            edges, start, end, weight, floor, max_detour_ratio=MAX_DETOUR_RATIO
        )

    def plan(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        *,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        recommended_kind: str,
        elevation: Elevation | None = None,
        extra_kinds: tuple[str, ...] = (),
        via_node: str | None = None,
        via_name: str | None = None,
    ) -> list[RouteOptionDto]:
        lookup = _lookup(edges)

        def kind_path(kind: str) -> list[str]:
            if via_node is None:
                return self._path_for(kind, edges, start, end, shade_lookup, elevation)
            first = self._path_for(kind, edges, start, via_node, shade_lookup, elevation)
            second = self._path_for(kind, edges, via_node, end, shade_lookup, elevation)
            return first + second[1:] if first and second else []

        fast = kind_path("fast")
        if not fast:
            return []
        prefs = (["shade"] if shade_lookup is not None else []) + ["green"]
        if elevation:  # 고도가 있어야 편한 길·언덕길을 계산할 수 있다
            prefs.append("flat")
            if "hilly" in extra_kinds or recommended_kind == "hilly":
                prefs.append("hilly")
        # 두 후보가 같은 길이면 먼저 계산한 쪽이 남는다 — 추천 종류를 앞에 둬서 그쪽 이름으로 남긴다.
        prefs.sort(key=lambda k: k != recommended_kind)
        kinds = ["fast", *prefs]
        kept: list[tuple[str, list[str], set[tuple[str, str]]]] = []
        for kind in kinds:
            path = fast if kind == "fast" else kind_path(kind)
            if not path:
                continue
            keys = {_edge_key(e) for e in path_edges(lookup, path)}
            if any(len(keys & k) / max(1, len(keys | k)) >= SIMILAR_JACCARD for _, _, k in kept):
                continue  # 이미 있는 후보와 사실상 같은 길
            kept.append((kind, path, keys))

        coords = {kind: path_coordinates(lookup, path) for kind, path, _ in kept}
        places = self._search_places(coords)
        # "바로 가는 길보다 N m 더"의 기준은 들르지 않는 최단 경로
        direct = self._path_for("fast", edges, start, end, None) if via_node else fast
        shortest_m = _length(lookup, direct or fast)
        kinds_kept = [k for k, _, _ in kept]
        rec = recommended_kind if recommended_kind in kinds_kept else kinds_kept[0]
        out = [
            self._build(
                kind,
                path,
                coords[kind],
                lookup,
                shade_lookup,
                shortest_m,
                places,
                rec == kind,
                via_name=via_name,
                elevation=elevation,
            )
            for kind, path, _ in kept
        ]
        logger.info(
            "[RouteOptions] %s→%s 후보 %s (추천 %s) 장소 %d곳",
            start,
            end,
            ",".join(f"{o.kind}:{round(o.length_m)}m" for o in out),
            rec,
            len(places),
        )
        return out

    def via(
        self,
        edges: list[RouteEdge],
        start: str,
        via_node: str,
        end: str,
        *,
        base_kind: str,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        via_name: str,
        elevation: Elevation | None = None,
    ) -> RouteOptionDto | None:
        lookup = _lookup(edges)
        first = self._path_for(base_kind, edges, start, via_node, shade_lookup, elevation)
        second = self._path_for(base_kind, edges, via_node, end, shade_lookup, elevation)
        if not first or not second:
            return None
        path = first + second[1:]
        coords = path_coordinates(lookup, path)
        shortest_m = _length(lookup, self._path_for("fast", edges, start, end, None))
        places = self._search_places({"via": coords})
        # 들렀다 가기는 사용자가 고른 경로라 '추천' 배지를 달지 않는다(원래 추천과 배지가 둘이 됐다)
        return self._build(
            "via",
            path,
            coords,
            lookup,
            shade_lookup,
            shortest_m,
            places,
            False,
            via_name=via_name,
            elevation=elevation,
        )

    def loops(
        self,
        edges: list[RouteEdge],
        start: str,
        *,
        target_m: float,
        max_m: float | None,
        preference: str,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        elevation: Elevation | None,
        stop_categories: tuple[str, ...],
        nearest_node: Callable[[Coordinate], str | None],
        limit: int = 3,
        preferences: tuple[str, ...] = (),
    ) -> list[RouteOptionDto]:
        """출발지로 돌아오는 목표 거리 루프 — 선호 가중치로 찾고, 들를 곳 종류를 지나는 루프를 앞에.

        `preferences`에 여러 선호가 오면 함께 적용한다(편한 길 + 그늘 많은 길). 후보의 종류(kind)는
        대표 선호(`preference`)로 두고 이름만 조합으로 바꾼다.
        """
        if self._loops is None:
            return []
        prefs = preferences or (preference,)
        weight, floor = make_combined_weight(prefs, shade_lookup=shade_lookup, elevation=elevation)
        found = self._loops.execute(
            edges,
            start,
            target_m,
            SeasonMode.SPRING_AUTUMN,  # weight_fn을 넘기므로 계절 가중치는 쓰이지 않는다
            nearest_node=nearest_node,
            shade_lookup=shade_lookup,
            limit=limit * 2,
            weight_fn=weight,
            heuristic_scale=floor,
        )
        if max_m:  # 제한 시간 안에 못 도는 루프는 뺀다(전부 넘으면 가장 짧은 하나만)
            within = [c for c in found if c.length_m <= max_m]
            found = within or sorted(found, key=lambda c: c.length_m)[:1]
        if not found:
            return []
        lookup = _lookup(edges)
        coords = {str(i): path_coordinates(lookup, c.path) for i, c in enumerate(found)}
        places = self._search_places(coords)
        built = [
            self._build(
                preference,
                c.path,
                coords[str(i)],
                lookup,
                shade_lookup,
                _length(lookup, c.path),
                places,
                False,
                elevation=elevation,
                loop_target_m=target_m,
            )
            for i, c in enumerate(found)
        ]
        if len(prefs) > 1:
            # 이름과 이유 문장의 성격 이름을 조합으로 바꾼다("편한 길 코스" → "편한 길 + 그늘 많은 길 코스")
            name = combined_label(prefs)
            built = [
                replace(o, label=name, reason=o.reason.replace(o.label, name, 1)) for o in built
            ]
        wanted = set(stop_categories)
        # 들를 곳을 지나는 루프 먼저, 그다음 고른 성격이 가장 뚜렷한 루프(모두 제한 시간 안).
        # 선호가 여럿이면 선호별 순위를 더해 고르게 맞는 루프를 앞에 둔다.
        order = _combined_order(prefs, built)
        built = [
            o
            for _, o in sorted(
                enumerate(built),
                key=lambda io: (-len(wanted & {p.category for p in io[1].places}), order[io[0]]),
            )
        ]
        out = built[:limit]
        out[0] = replace(out[0], recommended=True)
        logger.info(
            "[RouteOptions] 루프 %s 목표 %dm 선호 %s 들를곳 %s → %s",
            start,
            round(target_m),
            "+".join(prefs),
            ",".join(stop_categories) or "-",
            ",".join(f"{round(o.length_m)}m" for o in out),
        )
        return out

    # --- 수치·장소 ------------------------------------------------------------------------

    def _search_places(self, coords_by_kind: dict[str, list[list[float]]]) -> list[PetPlace]:
        pts = [c for cs in coords_by_kind.values() for c in cs]
        if not pts:
            return []
        lat = sum(p[0] for p in pts) / len(pts)
        lng = sum(p[1] for p in pts) / len(pts)
        center = Coordinate(lat, lng)
        reach = max(center.distance_to(Coordinate(p[0], p[1])) for p in pts)
        radius = int(min(2500.0, max(500.0, reach + PLACE_NEAR_M)))
        try:
            return self._places.search_around(center, radius)
        except Exception:  # noqa: BLE001 — 장소는 부가 정보라 실패해도 경로는 준다
            logger.warning("[RouteOptions] 장소 검색 실패", exc_info=True)
            return []

    def _build(
        self,
        kind: str,
        path: list[str],
        coords: list[list[float]],
        lookup: EdgeLookup,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        shortest_m: float,
        all_places: list[PetPlace],
        recommended: bool,
        *,
        via_name: str | None = None,
        elevation: Elevation | None = None,
        loop_target_m: float | None = None,
    ) -> RouteOptionDto:
        es = path_edges(lookup, path)
        length = sum(e.base_distance_m for e in es) or 1.0
        green = sum(e.base_distance_m * max(0.0, min(1.0, e.tree_score)) for e in es) / length
        shade: float | None = None
        if shade_lookup is not None:
            shaded = 0.0
            for e in es:
                s = shade_lookup.get((e.from_node, e.to_node))
                if s is None:
                    s = shade_lookup.get((e.to_node, e.from_node))
                shaded += e.base_distance_m * max(s or 0.0, e.tree_score)
            shade = shaded / length
        road_len: dict[str, float] = {}
        for e in es:
            if e.road_name:
                road_len[e.road_name] = road_len.get(e.road_name, 0.0) + e.base_distance_m
        roads = tuple(sorted(road_len, key=road_len.__getitem__, reverse=True)[:2])

        near: list[tuple[int, PetPlace]] = []
        for p in all_places:
            idx, dist = nearest_vertex(coords, p.coordinate)
            if idx >= 0 and dist <= PLACE_NEAR_M:
                near.append((idx, p))
        near.sort(key=lambda t: t[0])  # 가는 순서대로
        places = [p for _, p in near[:MAX_PLACES]]

        metrics = RouteOptionMetrics(
            length_m=length,
            shade_ratio=shade,
            green_ratio=green,
            roads=roads,
            place_categories=tuple(p.category for p in places),
            via_name=via_name,
            climb_m=climb_m(path, elevation) if elevation else None,
            loop_target_m=loop_target_m,
        )
        text = describe(kind, metrics, shortest_m)
        return RouteOptionDto(
            kind=kind,
            label=(
                f"{via_name} 들렀다 가기"
                if kind == "via"
                else (f"{text.label} · {via_name} 들러서" if via_name else text.label)
            ),
            reason=text.reason,
            highlights=text.highlights,
            recommended=recommended,
            path=path,
            coordinates=coords,
            length_m=round(length, 1),
            minutes=metrics.minutes,
            extra_m=round(max(0.0, length - shortest_m), 1),
            shade_ratio=round(shade, 2) if shade is not None else None,
            green_ratio=round(green, 2),
            places=places,
            climb_m=round(metrics.climb_m) if metrics.climb_m is not None else None,
        )


_lookup_cache: tuple[list[RouteEdge], EdgeLookup] | None = None


def _lookup(edges: list[RouteEdge]) -> EdgeLookup:
    """양방향 간선 색인 — 라우터 캐시가 같은 리스트 객체를 재사용하므로 동일성으로 캐시(23만 간선)."""
    global _lookup_cache  # noqa: PLW0603
    if _lookup_cache is not None and _lookup_cache[0] is edges:
        return _lookup_cache[1]
    lookup: EdgeLookup = {}
    for e in edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e
    _lookup_cache = (edges, lookup)
    return lookup


def _length(lookup: EdgeLookup, path: list[str]) -> float:
    return sum(e.base_distance_m for e in path_edges(lookup, path))


def _combined_order(prefs: tuple[str, ...], options: list[RouteOptionDto]) -> list[float]:
    """후보별 정렬 값 — 선호마다 매긴 순위(0이 가장 잘 맞음)의 합. 선호가 하나면 그 순위 그대로."""
    total = [0.0] * len(options)
    for p in prefs:
        ranked = sorted(range(len(options)), key=lambda i: _pref_rank(p, options[i]))
        for position, i in enumerate(ranked):
            total[i] += position
    return total


def _pref_rank(preference: str, o: RouteOptionDto) -> float:
    """작을수록 그 성격에 맞는 루프."""
    if preference == "flat" and o.climb_m is not None:
        return o.climb_m
    if preference == "hilly" and o.climb_m is not None:
        return -o.climb_m
    if preference == "shade" and o.shade_ratio is not None:
        return -o.shade_ratio
    if preference == "green":
        return -o.green_ratio
    return o.length_m
