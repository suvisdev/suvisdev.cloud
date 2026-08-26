"""EdgeScoreCalculator 단위 테스트 — TDD."""

import pytest

from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.tree_species import TreeSpecies
from gildle.scripts.compute_edge_scores import (
    EdgeScoreCalculator,
    load_scored_edges,
    save_scored_edges,
)

_YEOUIDO = Coordinate(latitude=37.5260, longitude=126.9258)
_YEOUIDO_NEARBY = Coordinate(latitude=37.5261, longitude=126.9259)
_GANGNAM = Coordinate(latitude=37.5010, longitude=127.0390)


def _edge(
    road_name: str | None = "여의대로",
    midpoint: Coordinate = _YEOUIDO,
) -> RouteEdge:
    return RouteEdge(
        from_node="A",
        to_node="B",
        base_distance_m=100.0,
        midpoint=midpoint,
        road_name=road_name,
    )


def _segment(
    road_name: str | None = "여의대로",
    species: TreeSpecies = TreeSpecies.CHERRY,
    quantity: int = 120,
    start: Coordinate = _YEOUIDO,
) -> TreeSegment:
    end = Coordinate(latitude=start.latitude + 0.0002, longitude=start.longitude + 0.0002)
    return TreeSegment(
        id=1,
        road_name=road_name,
        start=start,
        end=end,
        species=species,
        quantity=quantity,
        managing_agency="영등포구청",
    )


def _hazard(
    center: Coordinate = _YEOUIDO,
    radius: float = 200.0,
    accident_count: int = 8,
) -> HazardZone:
    return HazardZone(
        id=1,
        center=center,
        radius_meters=radius,
        accident_count=accident_count,
        description="결빙 다발지역",
    )


class TestComputeTreeScore:
    calc = EdgeScoreCalculator()

    def test_road_name_match_gives_positive_score(self):
        edge = _edge(road_name="여의대로")
        segment = _segment(road_name="여의대로", species=TreeSpecies.CHERRY, quantity=120)

        score = self.calc.compute_tree_score(edge, [segment])

        assert score > 0.0

    def test_no_matching_segment_gives_zero(self):
        edge = _edge(road_name="국회대로", midpoint=_GANGNAM)
        segment = _segment(road_name="여의대로", species=TreeSpecies.CHERRY)

        score = self.calc.compute_tree_score(edge, [segment])

        assert score == 0.0

    def test_empty_segments_gives_zero(self):
        assert self.calc.compute_tree_score(_edge(), []) == 0.0

    def test_proximity_fallback_when_no_road_name(self):
        edge = _edge(road_name=None, midpoint=_YEOUIDO)
        segment = _segment(road_name=None, start=_YEOUIDO)

        score = self.calc.compute_tree_score(edge, [segment])

        assert score > 0.0

    def test_proximity_beyond_threshold_gives_zero(self):
        edge = _edge(road_name=None, midpoint=_YEOUIDO)
        segment = _segment(road_name=None, start=_GANGNAM)

        score = self.calc.compute_tree_score(edge, [segment])

        assert score == 0.0

    def test_bonus_species_ratio_increases_score(self):
        edge = _edge(road_name="여의대로")
        all_bonus = [
            _segment(species=TreeSpecies.CHERRY, quantity=100),
            _segment(species=TreeSpecies.ZELKOVA, quantity=100),
        ]
        mixed = [
            _segment(species=TreeSpecies.CHERRY, quantity=100),
            _segment(species=TreeSpecies.GINKGO, quantity=100),
        ]

        score_all_bonus = self.calc.compute_tree_score(edge, all_bonus)
        score_mixed = self.calc.compute_tree_score(edge, mixed)

        assert score_all_bonus > score_mixed

    def test_score_clamped_to_0_1(self):
        edge = _edge()
        huge = _segment(quantity=99999)

        score = self.calc.compute_tree_score(edge, [huge])

        assert 0.0 <= score <= 1.0


class TestComputeHazardScore:
    calc = EdgeScoreCalculator()

    def test_edge_at_hazard_center_gives_max_score(self):
        edge = _edge(midpoint=_YEOUIDO)
        hazard = _hazard(center=_YEOUIDO)

        score = self.calc.compute_hazard_score(edge, [hazard])

        assert score == pytest.approx(1.0)

    def test_edge_at_hazard_boundary_gives_near_zero(self):
        center = _YEOUIDO
        hazard = _hazard(center=center, radius=200.0)
        boundary_lat = center.latitude + 0.0017
        edge = _edge(midpoint=Coordinate(latitude=boundary_lat, longitude=center.longitude))
        distance = edge.midpoint.distance_to(center)
        assert 170.0 < distance < 200.0

        score = self.calc.compute_hazard_score(edge, [hazard])

        assert 0.0 < score < 0.2

    def test_edge_outside_hazard_gives_zero(self):
        edge = _edge(midpoint=_GANGNAM)
        hazard = _hazard(center=_YEOUIDO, radius=200.0)

        score = self.calc.compute_hazard_score(edge, [hazard])

        assert score == 0.0

    def test_no_hazards_gives_zero(self):
        assert self.calc.compute_hazard_score(_edge(), []) == 0.0

    def test_overlapping_hazards_takes_max(self):
        edge = _edge(midpoint=_YEOUIDO)
        far = _hazard(
            center=Coordinate(latitude=_YEOUIDO.latitude + 0.001, longitude=_YEOUIDO.longitude),
            radius=200.0,
        )
        close = _hazard(center=_YEOUIDO, radius=200.0)

        score = self.calc.compute_hazard_score(edge, [far, close])

        assert score == pytest.approx(1.0)

    def test_score_clamped_to_0_1(self):
        edge = _edge(midpoint=_YEOUIDO)
        hazard = _hazard(center=_YEOUIDO)

        score = self.calc.compute_hazard_score(edge, [hazard])

        assert 0.0 <= score <= 1.0


class TestComputeDogFriendlyScore:
    calc = EdgeScoreCalculator()

    def test_zero_tree_score_gives_base_0_3(self):
        assert self.calc.compute_dog_friendly_score(0.0) == pytest.approx(0.3)

    def test_max_tree_score_gives_1_0(self):
        assert self.calc.compute_dog_friendly_score(1.0) == pytest.approx(1.0)

    def test_mid_tree_score(self):
        assert self.calc.compute_dog_friendly_score(0.5) == pytest.approx(0.65)

    def test_score_clamped_to_0_1(self):
        score = self.calc.compute_dog_friendly_score(1.5)
        assert 0.0 <= score <= 1.0


class TestScoreEdges:
    calc = EdgeScoreCalculator()

    def test_returns_new_edges_with_scores_filled(self):
        edges = [_edge(road_name="여의대로")]
        segments = [_segment(road_name="여의대로", species=TreeSpecies.CHERRY)]
        hazards = [_hazard(center=_YEOUIDO)]

        scored = self.calc.score_edges(edges, segments, hazards)

        assert len(scored) == 1
        assert scored[0].tree_score > 0.0
        assert scored[0].hazard_score > 0.0
        assert scored[0].dog_friendly_score > 0.0

    def test_preserves_original_edge_fields(self):
        original = _edge(road_name="여의대로")
        scored = self.calc.score_edges([original], [_segment()], [])

        assert scored[0].from_node == original.from_node
        assert scored[0].to_node == original.to_node
        assert scored[0].base_distance_m == original.base_distance_m
        assert scored[0].midpoint == original.midpoint
        assert scored[0].road_name == original.road_name

    def test_idempotent(self):
        edges = [_edge()]
        segments = [_segment()]
        hazards = [_hazard()]

        first_run = self.calc.score_edges(edges, segments, hazards)
        second_run = self.calc.score_edges(edges, segments, hazards)

        assert len(first_run) == len(second_run)
        for a, b in zip(first_run, second_run, strict=False):
            assert a.tree_score == b.tree_score
            assert a.hazard_score == b.hazard_score
            assert a.dog_friendly_score == b.dog_friendly_score

    def test_unmatched_edge_gets_zeros_and_base_dog(self):
        edge = _edge(road_name="없는도로", midpoint=_GANGNAM)
        scored = self.calc.score_edges([edge], [], [])

        assert scored[0].tree_score == 0.0
        assert scored[0].hazard_score == 0.0
        assert scored[0].dog_friendly_score == pytest.approx(0.3)


class TestSaveAndLoadScoredEdges:
    calc = EdgeScoreCalculator()

    def test_roundtrip_preserves_scores(self, tmp_path):
        edges = [_edge(road_name="여의대로")]
        segments = [_segment(species=TreeSpecies.CHERRY)]
        hazards = [_hazard(center=_YEOUIDO)]
        scored = self.calc.score_edges(edges, segments, hazards)

        path = tmp_path / "scored.json"
        save_scored_edges(scored, path)
        loaded = load_scored_edges(path)

        assert len(loaded) == 1
        assert loaded[0].from_node == scored[0].from_node
        assert loaded[0].to_node == scored[0].to_node
        assert loaded[0].base_distance_m == scored[0].base_distance_m
        assert loaded[0].midpoint == scored[0].midpoint
        assert loaded[0].road_name == scored[0].road_name
        assert loaded[0].tree_score == pytest.approx(scored[0].tree_score, abs=1e-5)
        assert loaded[0].hazard_score == pytest.approx(scored[0].hazard_score, abs=1e-5)
        assert loaded[0].dog_friendly_score == pytest.approx(scored[0].dog_friendly_score, abs=1e-5)

    def test_save_twice_is_idempotent(self, tmp_path):
        edges = [_edge()]
        scored = self.calc.score_edges(edges, [_segment()], [_hazard()])

        path = tmp_path / "scored.json"
        save_scored_edges(scored, path)
        first_content = path.read_text()
        save_scored_edges(scored, path)
        second_content = path.read_text()

        assert first_content == second_content
