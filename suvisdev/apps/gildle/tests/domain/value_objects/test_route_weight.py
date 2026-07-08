from dataclasses import FrozenInstanceError

import pytest

from gildle.domain.value_objects.route_weight import RouteWeight


class TestRouteWeight:
    def test_valid_weight(self):
        assert RouteWeight(100.0).value == 100.0

    def test_zero_is_valid(self):
        assert RouteWeight(0.0).value == 0.0

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="음수"):
            RouteWeight(-1.0)

    def test_apply_discount_returns_new_instance(self):
        original = RouteWeight(100.0)
        discounted = original.apply_discount(0.3)
        assert discounted.value == pytest.approx(70.0)
        assert original.value == 100.0  # 불변
        assert discounted is not original

    def test_apply_penalty_returns_new_instance(self):
        original = RouteWeight(100.0)
        penalized = original.apply_penalty(5.0)
        assert penalized.value == pytest.approx(600.0)  # 500% 증가 = 6배
        assert original.value == 100.0  # 불변
        assert penalized is not original

    def test_is_frozen(self):
        weight = RouteWeight(10.0)
        with pytest.raises(FrozenInstanceError):
            weight.value = 20.0  # type: ignore[misc]
