import pytest

from gildle.domain.value_objects.tree_species import TreeSpecies


class TestTreeSpecies:
    def test_values_are_korean_labels(self):
        assert TreeSpecies.CHERRY.value == "벚나무"
        assert TreeSpecies.ZELKOVA.value == "느티나무"
        assert TreeSpecies.GINKGO.value == "은행나무"

    def test_cherry_is_bonus_species(self):
        assert TreeSpecies.CHERRY.is_bonus_species is True

    def test_zelkova_is_bonus_species(self):
        assert TreeSpecies.ZELKOVA.is_bonus_species is True

    def test_ginkgo_is_not_bonus_species(self):
        assert TreeSpecies.GINKGO.is_bonus_species is False

    def test_from_label_resolves_korean(self):
        assert TreeSpecies.from_label("벚나무") is TreeSpecies.CHERRY
        assert TreeSpecies.from_label("느티나무") is TreeSpecies.ZELKOVA

    def test_from_label_strips_whitespace(self):
        assert TreeSpecies.from_label("  은행나무 ") is TreeSpecies.GINKGO

    def test_from_label_unknown_raises(self):
        with pytest.raises(ValueError, match="수종"):
            TreeSpecies.from_label("소나무")
