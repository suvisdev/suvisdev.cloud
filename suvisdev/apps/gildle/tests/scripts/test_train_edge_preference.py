"""모델 A 파이프라인 — 가상 walks로 학습이 '그늘 선호'를 되찾는지."""

from __future__ import annotations

from gildle.scripts.train_edge_preference import (
    FEATURES,
    build_examples,
    fit_logistic,
    implied_multipliers,
    match_path_to_edges,
    synthetic_walks,
)


def test_synthetic_user_shade_preference_is_recovered() -> None:
    walks, edges, shade = synthetic_walks(seed=3, n=40)
    examples = build_examples(walks, edges, shade)
    assert len(examples) > 40
    assert any(y == 0 for _, y in examples), "반사실(최단경로) 음성 예시가 없다"
    coef = fit_logistic(examples)
    mult = implied_multipliers(coef)
    # 가상 사용자는 햇빛 간선을 3배 비싸게 느낀다 → 그늘 계수 양수 → 배율 < 1
    assert coef[FEATURES.index("shade")] > 0, coef
    assert mult["shade"] < 1.0, mult


def test_match_path_snaps_to_nearest_edges_once() -> None:
    walks, edges, _ = synthetic_walks(seed=1, n=1)
    matched = match_path_to_edges(walks[0]["path"], edges)
    assert len(matched) == len(walks[0]["path"])
    assert len({id(e) for e in matched}) == len(matched)
