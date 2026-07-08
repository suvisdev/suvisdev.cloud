import pytest

from gildle.domain.value_objects.season_mode import SeasonMode


class TestSeasonMode:
    def test_values(self):
        assert SeasonMode.SPRING_AUTUMN.value == "spring_autumn"
        assert SeasonMode.WINTER_SAFETY.value == "winter_safety"

    def test_from_value(self):
        assert SeasonMode.from_value("spring_autumn") is SeasonMode.SPRING_AUTUMN
        assert SeasonMode.from_value("winter_safety") is SeasonMode.WINTER_SAFETY

    def test_from_value_unknown_raises(self):
        with pytest.raises(ValueError, match="모드"):
            SeasonMode.from_value("summer")
