"""경로 후보 — 빠른 길 · 그늘 많은 길 · 푸른 길을 나란히 계산하고 고를 이유를 붙인다(2026-09-28).

사용자 요청: "이쪽으로 갈 땐 이런 좋은 점, 저쪽으로 갈 땐 이런 좋은 점 — 둘 중 골라서 산책". 경로를
고르는 건 모델이 아니라 그래프 탐색이다. 후보마다 다른 가중치(거리·그늘·수관)로 A*를 돌리고, 길이는
최단거리의 1.5배를 넘지 않게 묶는다. 이유 문장은 계산한 수치로만 만든다(route_option_describer).
경로 곁 50~150m의 동물병원·펫샵·용품점·애견카페를 함께 붙이고, 고르면 들렀다 가는 경로를 만든다.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping

from gildle.app.dtos.route_option_dto import RouteOptionDto
from gildle.app.ports.input.calculate_route_use_case import CalculateDogFriendlyRouteUseCase
from gildle.app.ports.input.route_options_use_case import RouteOptionsUseCase
from gildle.app.ports.output.pet_place_port import PetPlacePort
from gildle.domain.services.route_geometry import (
    EdgeLookup,
    nearest_vertex,
    path_coordinates,
    path_edges,
)
from gildle.domain.services.route_option_describer import RouteOptionMetrics, describe
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
    def __init__(self, route: CalculateDogFriendlyRouteUseCase, places: PetPlacePort) -> None:
        self._route = route
        self._places = places

    # --- 후보 계산 -------------------------------------------------------------------------

    def _path_for(
        self,
        kind: str,
        edges: list[RouteEdge],
        start: str,
        end: str,
        shade_lookup: Mapping[tuple[str, str], float] | None,
    ) -> list[str]:
        if kind == "shade":
            return self._route.execute_bounded(
                edges,
                start,
                end,
                SeasonMode.SUMMER_SHADE,
                shade_lookup=shade_lookup,
                max_detour_ratio=MAX_DETOUR_RATIO,
            )
        if kind == "green":
            return self._route.execute_bounded(
                edges, start, end, SeasonMode.SPRING_AUTUMN, max_detour_ratio=MAX_DETOUR_RATIO
            )
        return self._route.execute_shortest(edges, start, end)

    def plan(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        *,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        recommended_kind: str,
    ) -> list[RouteOptionDto]:
        lookup = _lookup(edges)
        fast = self._path_for("fast", edges, start, end, None)
        if not fast:
            return []
        prefs = (["shade"] if shade_lookup is not None else []) + ["green"]
        # 두 후보가 같은 길이면 먼저 계산한 쪽이 남는다 — 추천 종류를 앞에 둬서 그쪽 이름으로 남긴다.
        prefs.sort(key=lambda k: k != recommended_kind)
        kinds = ["fast", *prefs]
        kept: list[tuple[str, list[str], set[tuple[str, str]]]] = []
        for kind in kinds:
            path = fast if kind == "fast" else self._path_for(kind, edges, start, end, shade_lookup)
            if not path:
                continue
            keys = {_edge_key(e) for e in path_edges(lookup, path)}
            if any(len(keys & k) / max(1, len(keys | k)) >= SIMILAR_JACCARD for _, _, k in kept):
                continue  # 이미 있는 후보와 사실상 같은 길
            kept.append((kind, path, keys))

        coords = {kind: path_coordinates(lookup, path) for kind, path, _ in kept}
        places = self._search_places(coords)
        shortest_m = _length(lookup, fast)
        kinds_kept = [k for k, _, _ in kept]
        rec = recommended_kind if recommended_kind in kinds_kept else kinds_kept[0]
        out = [
            self._build(
                kind, path, coords[kind], lookup, shade_lookup, shortest_m, places, rec == kind
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
        via_point: Coordinate,
    ) -> RouteOptionDto | None:
        lookup = _lookup(edges)
        first = self._path_for(base_kind, edges, start, via_node, shade_lookup)
        second = self._path_for(base_kind, edges, via_node, end, shade_lookup)
        if not first or not second:
            return None
        path = first + second[1:]
        coords = path_coordinates(lookup, path)
        shortest_m = _length(lookup, self._path_for("fast", edges, start, end, None))
        places = self._search_places({"via": coords})
        # 들렀다 가기는 사용자가 고른 경로라 '추천' 배지를 달지 않는다(원래 추천과 배지가 둘이 됐다)
        return self._build(
            "via", path, coords, lookup, shade_lookup, shortest_m, places, False, via_name=via_name
        )

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
        road_len: Counter[str] = Counter()
        for e in es:
            if e.road_name:
                road_len[e.road_name] += e.base_distance_m
        roads = tuple(name for name, _ in road_len.most_common(2))

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
        )
        text = describe(kind, metrics, shortest_m)
        return RouteOptionDto(
            kind=kind,
            label=text.label if kind != "via" else f"{via_name} 들렀다 가기",
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
