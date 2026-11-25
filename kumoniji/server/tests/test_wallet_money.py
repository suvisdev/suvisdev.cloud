from kumoniji.wallet import money


def test_regen_one_heart_per_ten_minutes_up_to_ten():
    assert money.regen(3, 0, 599) == (3, 0)
    assert money.regen(3, 0, 1300) == (5, 1200)  # 2개 차고 남은 100초는 다음 충전으로
    assert money.regen(9, 0, 10_000)[0] == 10  # 10에서 멈춤
    assert money.regen(12, 0, 10_000) == (12, 10_000)  # 산 하트는 10을 넘어 그대로, 충전 없음
    assert money.regen(10, 500, 400) == (10, 500)  # 늦게 잠근 옛 요청이 기준 시각을 되돌리지 않는다
    assert money.regen(0, 100, 99.5) == (0, 100)  # 먼저 잠근 요청이 기준 시각을 앞으로 옮겨도 줄지 않는다


def test_stake_is_points_times_50_and_zero_sum():
    assert money.stake([60, -10, -20, -30], [10**6] * 4) == [3000, -500, -1000, -1500]


def test_stake_never_takes_more_than_balance_and_winners_share_what_was_paid():
    # 3번은 1,500을 내야 하지만 200뿐 → 200만. 받는 사람(0번)은 실제로 걷힌 500+1000+200
    assert money.stake([60, -10, -20, -30], [0, 10**6, 10**6, 200]) == [1700, -500, -1000, -200]
    # 받는 사람이 둘이면 점수 비율로, 남는 1은 많이 받는 쪽에
    assert money.stake([20, 10, -15, -15], [0, 0, 10**6, 101]) == [568, 283, -750, -101]
