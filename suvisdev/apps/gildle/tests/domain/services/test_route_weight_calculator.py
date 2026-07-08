from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode
from gildle.domain.value_objects.tree_species import TreeSpecies


def _edge(midpoint: Coordinate, road_name=None, base=100.0) -> RouteEdge:
    return RouteEdge(
        from_node="A",
        to_node="B",
        base_distance_m=base,
        midpoint=midpoint,
        road_name=road_name,
    )


def _segment(point: Coordinate, species: TreeSpecies, road_name=None) -> TreeSegment:
    return TreeSegment(
        id=1,
        road_name=road_name,
        start=point,
        end=point,  # start==end → midpoint == point
        species=species,
        quantity=10,
        managing_agency="구청",
    )


class TestSpringAutumnRoadNameMatch:
    """도로명 매칭(우선 규칙)."""

    def test_bonus_species_same_road_name_gets_30pct_discount(self):
        calc = RouteWeightCalculator()
        far_point = Coordinate(latitude=38.0, longitude=128.0)  # 좌표는 멀어도
        edge = _edge(Coordinate(latitude=37.5, longitude=127.0), road_name="여의대로")
        seg = _segment(far_point, TreeSpecies.CHERRY, road_name="여의대로")

        weight = calc.calculate_edge_weight(edge, SeasonMode.SPRING_AUTUMN, [seg], [])

        assert weight.value == 70.0  # 도로명만 맞으면 좌표가 멀어도 감면

    def test_non_bonus_species_same_road_name_no_discount(self):
        calc = RouteWeightCalculator()
        point = Coordinate(latitude=37.5, longitude=127.0)
        edge = _edge(point, road_name="은행로")
        seg = _segment(point, TreeSpecies.GINKGO, road_name="은행로")

        weight = calc.calculate_edge_weight(edge, SeasonMode.SPRING_AUTUMN, [seg], [])

        assert weight.value == 100.0


class TestSpringAutumnProximityMatch:
    """좌표 근접 매칭(보조 규칙)."""

    def test_bonus_species_within_10m_gets_discount_when_no_road_name(self):
        calc = RouteWeightCalculator()
        edge_mid = Coordinate(latitude=37.50000, longitude=127.0)
        # 위도 0.00005도 ≈ 5.56m < 10m
        seg_point = Coordinate(latitude=37.50005, longitude=127.0)
        edge = _edge(edge_mid, road_name=None)
        seg = _segment(seg_point, TreeSpecies.ZELKOVA, road_name=None)

        weight = calc.calculate_edge_weight(edge, SeasonMode.SPRING_AUTUMN, [seg], [])

        assert weight.value == 70.0

    def test_bonus_species_beyond_10m_no_discount(self):
        calc = RouteWeightCalculator()
        edge_mid = Coordinate(latitude=37.5000, longitude=127.0)
        # 위도 0.0002도 ≈ 22m > 10m
        seg_point = Coordinate(latitude=37.5002, longitude=127.0)
        edge = _edge(edge_mid, road_name=None)
        seg = _segment(seg_point, TreeSpecies.CHERRY, road_name=None)

        weight = calc.calculate_edge_weight(edge, SeasonMode.SPRING_AUTUMN, [seg], [])

        assert weight.value == 100.0

    def test_road_name_mismatch_falls_back_to_proximity(self):
        calc = RouteWeightCalculator()
        edge_mid = Coordinate(latitude=37.50000, longitude=127.0)
        seg_point = Coordinate(latitude=37.50005, longitude=127.0)  # ≈5.56m
        edge = _edge(edge_mid, road_name="여의대로")
        # 도로명은 다르지만 좌표가 가까움 → 보조 규칙으로 매칭
        seg = _segment(seg_point, TreeSpecies.CHERRY, road_name="국회대로")

        weight = calc.calculate_edge_weight(edge, SeasonMode.SPRING_AUTUMN, [seg], [])

        assert weight.value == 70.0


class TestWinterSafety:
    def test_hazard_within_20m_gets_500pct_penalty(self):
        calc = RouteWeightCalculator()
        edge_mid = Coordinate(latitude=37.50000, longitude=127.0)
        # 위도 0.0001도 ≈ 11m < 20m
        hazard = HazardZone(
            id=1,
            center=Coordinate(latitude=37.50010, longitude=127.0),
            radius_meters=200.0,
            accident_count=3,
            description="결빙",
        )
        edge = _edge(edge_mid)

        weight = calc.calculate_edge_weight(edge, SeasonMode.WINTER_SAFETY, [], [hazard])

        assert weight.value == 600.0  # 500% 증가 = 6배

    def test_hazard_beyond_20m_no_penalty(self):
        calc = RouteWeightCalculator()
        edge_mid = Coordinate(latitude=37.5000, longitude=127.0)
        # 위도 0.0005도 ≈ 55m > 20m
        hazard = HazardZone(
            id=1,
            center=Coordinate(latitude=37.5005, longitude=127.0),
            radius_meters=200.0,
            accident_count=3,
            description="결빙",
        )
        edge = _edge(edge_mid)

        weight = calc.calculate_edge_weight(edge, SeasonMode.WINTER_SAFETY, [], [hazard])

        assert weight.value == 100.0

    def test_winter_mode_ignores_tree_segments(self):
        calc = RouteWeightCalculator()
        point = Coordinate(latitude=37.5, longitude=127.0)
        edge = _edge(point, road_name="여의대로")
        seg = _segment(point, TreeSpecies.CHERRY, road_name="여의대로")

        weight = calc.calculate_edge_weight(edge, SeasonMode.WINTER_SAFETY, [seg], [])

        assert weight.value == 100.0  # 겨울 모드는 수종 감면 없음
