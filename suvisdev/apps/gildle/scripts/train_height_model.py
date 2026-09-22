"""모델 B — 건물 높이 결측 보간을 격자 중앙값에서 GBM 회귀로 바꿀 수 있는지 잰다.

`compute_shade_scores.impute_heights`는 250m 격자 실측 중앙값으로 결측(약 11%)을
채운다. 여기서는 브이월드 층수가 있는 건물(약 89%)로 학습하고 무작위 20% 홀드아웃에서
**모델 MAE vs 격자 중앙값 MAE**를 비교한다. 이기지 못하면 채택하지 않는다
(`_docs/GILDLE_ROUTING_ALGORITHM.md` §2-B, §3-⑥).

특징(외곽선만으로 만든다 — 브이월드 원본 필드는 저장하지 않았다):
  바닥면적·둘레·꼭짓점 수·compactness(4πA/P²)·bbox 종횡비·centroid(km)·
  같은 250m 격자의 실측 동 수·격자 중앙값·격자 평균·1km 격자 중앙값

    python -m gildle.scripts.train_height_model [--sample 200000] [--apply]
      --apply : 결측 건물 예측치를 data/height_model_pred.json에 쓴다(채택 시에만)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from pathlib import Path
from typing import Any

# compute_shade_scores는 모듈 상단에서 shapely를 import한다(서빙 이미지에 없음) —
# 여기서 필요한 건 원점·등장방형 투영 두 줄뿐이라 같은 식을 둔다.
_SEOUL_CENTER = (37.5665, 126.9780)


def project_to_meters(lat: float, lng: float, lat0: float, lng0: float) -> tuple[float, float]:
    return (lng - lng0) * 111320.0 * math.cos(math.radians(lat0)), (lat - lat0) * 110540.0


_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_BUILDINGS = _DATA_DIR / "seoul_buildings_osm.json"
_MODEL_OUT = _DATA_DIR / "height_model.lgb.txt"
_PRED_OUT = _DATA_DIR / "height_model_pred.json"
_REPORT_OUT = _DATA_DIR / "height_model_report.json"
_CELL_M = 250.0
_CELL_COARSE_M = 1000.0
_MAX_H = 150.0


def _geometry(outline: list[list[float]], lat0: float, lng0: float) -> dict[str, float]:
    pts = [project_to_meters(p[0], p[1], lat0, lng0) for p in outline]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    area = (
        abs(
            sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        )
        / 2
    )
    perim = sum(math.dist(pts[i], pts[(i + 1) % n]) for i in range(n))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = (max(xs) - min(xs)) or 1e-6, (max(ys) - min(ys)) or 1e-6
    cx, cy = sum(xs) / n, sum(ys) / n
    return {
        "area": area,
        "perim": perim,
        "nverts": float(n),
        "compact": (4 * math.pi * area / (perim * perim)) if perim > 0 else 0.0,
        "aspect": max(w, h) / min(w, h),
        "cx_km": cx / 1000.0,
        "cy_km": cy / 1000.0,
        "_cx": cx,
        "_cy": cy,
    }


def build_features(
    buildings: list[dict[str, Any]], train_idx: set[int]
) -> tuple[list[list[float]], list[str]]:
    """격자 통계는 **학습 집합의 실측만**으로 만든다(홀드아웃 누수 방지)."""
    lat0, lng0 = _SEOUL_CENTER
    geoms = [_geometry(b["outline"], lat0, lng0) for b in buildings]
    fine: dict[tuple[int, int], list[float]] = {}
    coarse: dict[tuple[int, int], list[float]] = {}
    for i in train_idx:
        g = geoms[i]
        fine.setdefault((int(g["_cx"] // _CELL_M), int(g["_cy"] // _CELL_M)), []).append(
            buildings[i]["height_m"]
        )
        coarse.setdefault(
            (int(g["_cx"] // _CELL_COARSE_M), int(g["_cy"] // _CELL_COARSE_M)), []
        ).append(buildings[i]["height_m"])
    all_train = [buildings[i]["height_m"] for i in train_idx]
    gmed = statistics.median(all_train) if all_train else 6.0
    fmed = {k: statistics.median(v) for k, v in fine.items()}
    fmean = {k: sum(v) / len(v) for k, v in fine.items()}
    cmed = {k: statistics.median(v) for k, v in coarse.items()}
    names = [
        "area",
        "perim",
        "nverts",
        "compact",
        "aspect",
        "cx_km",
        "cy_km",
        "cell_n",
        "cell_median",
        "cell_mean",
        "coarse_median",
    ]
    rows: list[list[float]] = []
    for g in geoms:
        fk = (int(g["_cx"] // _CELL_M), int(g["_cy"] // _CELL_M))
        ck = (int(g["_cx"] // _CELL_COARSE_M), int(g["_cy"] // _CELL_COARSE_M))
        rows.append(
            [
                g["area"],
                g["perim"],
                g["nverts"],
                g["compact"],
                g["aspect"],
                g["cx_km"],
                g["cy_km"],
                float(len(fine.get(fk, []))),
                fmed.get(fk, gmed),
                fmean.get(fk, gmed),
                cmed.get(ck, gmed),
            ]
        )
    return rows, names


def baseline_predict(rows: list[list[float]], names: list[str]) -> list[float]:
    """운영 impute_heights와 같은 규칙: 격자 실측 3동 이상이면 격자 중앙값, 아니면 전역."""
    i_n, i_med = names.index("cell_n"), names.index("cell_median")
    return [
        min(r[i_med], _MAX_H) if r[i_n] >= 3 else min(r[names.index("coarse_median")], _MAX_H)
        for r in rows
    ]


def _compare_candidates(x_tr, y_tr, x_ho, y_ho, base, names, seed) -> None:
    """같은 홀드아웃에서 후보를 나란히 잰다 — 사용자가 고를 수 있게(2026-09-22)."""
    import lightgbm as lgb
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.neighbors import KNeighborsRegressor

    xtr, xho = np.asarray(x_tr), np.asarray(x_ho)
    i_x, i_y, i_area = names.index("cx_km"), names.index("cy_km"), names.index("area")
    # kNN은 좌표(km)+log면적만 — "가까운 건물은 비슷한 높이"라는 가정 하나로 된 모델
    knn_tr = np.column_stack([xtr[:, i_x], xtr[:, i_y], np.log1p(xtr[:, i_area]) / 10])
    knn_ho = np.column_stack([xho[:, i_x], xho[:, i_y], np.log1p(xho[:, i_area]) / 10])
    cands = {
        "격자 중앙값(현행)": None,
        "선형(Ridge)": Ridge(alpha=1.0),
        "kNN 공간(k=15)": KNeighborsRegressor(n_neighbors=15, weights="distance"),
        "HistGBM(sklearn)": HistGradientBoostingRegressor(
            loss="absolute_error", max_iter=400, random_state=seed
        ),
        "LightGBM(L1)": lgb.LGBMRegressor(
            objective="l1",
            n_estimators=600,
            learning_rate=0.05,
            num_leaves=63,
            min_child_samples=40,
            verbose=-1,
            random_state=seed,
        ),
    }
    print(f"\n{'모델':18} {'MAE(m)':>8} {'±1층':>7} {'학습(s)':>8}")
    raw: dict[str, list[float]] = {}
    for name, m in cands.items():
        t0 = time.perf_counter()
        if m is None:
            pred = base
        elif name.startswith("kNN"):
            m.fit(knn_tr, y_tr)
            pred = m.predict(knn_ho)
        else:
            m.fit(xtr, y_tr)
            pred = m.predict(xho)
        raw[name] = [float(v) for v in pred]
        pred = [max(3.0, round(min(float(p), _MAX_H) / 3.0) * 3.0) for p in pred]  # 층 반올림 통일
        mae = _mae(y_ho, pred)
        hit = sum(1 for a, b in zip(y_ho, pred, strict=True) if abs(a - b) <= 3.0) / len(y_ho)
        print(f"{name:18} {mae:8.2f} {hit:7.1%} {time.perf_counter() - t0:8.1f}")
    # 앙상블(kNN·LightGBM 평균) — 사용자 요청(2026-09-22): 둘 중 더 정확한 쪽, 앙상블이 낫다면 앙상블
    ens = [
        max(3.0, round(min((a + b) / 2, _MAX_H) / 3.0) * 3.0)
        for a, b in zip(raw["kNN 공간(k=15)"], raw["LightGBM(L1)"], strict=True)
    ]
    mae = _mae(y_ho, ens)
    hit = sum(1 for a, b in zip(y_ho, ens, strict=True) if abs(a - b) <= 3.0) / len(y_ho)
    print(f"{'kNN+LightGBM 평균':18} {mae:8.2f} {hit:7.1%} {'-':>8}")


def _knn_matrix(rows: list[list[float]], names: list[str]):
    import numpy as np

    x = np.asarray(rows)
    i_x, i_y, i_area = names.index("cx_km"), names.index("cy_km"), names.index("area")
    return np.column_stack([x[:, i_x], x[:, i_y], np.log1p(x[:, i_area]) / 10])


def _predict_unknown(kind: str, lgb_model, rows, names, x_tr, y_tr, unknown, seed) -> list[float]:
    """--model 선택에 따라 결측 건물 예측치를 만든다(kNN은 좌표+log면적만 쓴다)."""
    x_unk = [rows[i] for i in unknown]
    lgb_pred = [float(v) for v in lgb_model.predict(x_unk)]
    if kind == "lgb":
        return lgb_pred
    from sklearn.neighbors import KNeighborsRegressor

    knn = KNeighborsRegressor(n_neighbors=15, weights="distance")
    knn.fit(_knn_matrix(x_tr, names), y_tr)
    knn_pred = [float(v) for v in knn.predict(_knn_matrix(x_unk, names))]
    if kind == "knn":
        return knn_pred
    return [(a + b) / 2 for a, b in zip(knn_pred, lgb_pred, strict=True)]


def _mae(y: list[float], p: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(y, p, strict=True)) / len(y)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=0, help="실측 건물 표본 수(0=전체)")
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--compare", action="store_true", help="후보 모델 5종 홀드아웃 비교표 출력")
    ap.add_argument(
        "--model",
        choices=["lgb", "knn", "ensemble"],
        default="ensemble",
        help="--apply에 쓸 예측기. 2026-09-22 홀드아웃: 앙상블 3.41m < kNN 3.46m < LightGBM 3.62m",
    )
    args = ap.parse_args()

    import lightgbm as lgb

    t0 = time.perf_counter()
    buildings: list[dict[str, Any]] = json.loads(_BUILDINGS.read_text(encoding="utf-8"))
    known = [i for i, b in enumerate(buildings) if b.get("height_known")]
    unknown = [i for i, b in enumerate(buildings) if not b.get("height_known")]
    rng = random.Random(args.seed)
    if args.sample and args.sample < len(known):
        known = rng.sample(known, args.sample)
    rng.shuffle(known)
    n_hold = len(known) // 5
    hold, train = known[:n_hold], known[n_hold:]
    print(
        f"[data] 전체 {len(buildings):,} · 실측 {len(known):,} (학습 {len(train):,} / 홀드아웃 {n_hold:,}) · 결측 {len(unknown):,}"
    )

    rows, names = build_features(buildings, set(train))
    y = [buildings[i]["height_m"] for i in range(len(buildings))]
    x_tr, y_tr = [rows[i] for i in train], [y[i] for i in train]
    x_ho, y_ho = [rows[i] for i in hold], [y[i] for i in hold]
    print(f"[feat] {len(names)}개 특징, {time.perf_counter() - t0:.0f}s")

    base = baseline_predict(x_ho, names)
    if args.compare:
        _compare_candidates(x_tr, y_tr, x_ho, y_ho, base, names, args.seed)
    model = lgb.LGBMRegressor(
        objective="l1",
        n_estimators=600,
        learning_rate=0.05,
        num_leaves=63,
        min_child_samples=40,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.9,
        verbose=-1,
        random_state=args.seed,
    )
    model.fit(x_tr, y_tr, feature_name=names)
    pred = [min(max(float(p), 3.0), _MAX_H) for p in model.predict(x_ho)]

    # 층수×3m 데이터라 정답이 3의 배수다 — 연속 예측을 층 단위로 반올림한 변형도 같이 잰다
    # (L1 회귀는 큰 오차를 줄이지만 "정확히 그 층"을 맞히는 비율은 중앙값에 질 수 있다).
    pred_floor = [max(3.0, round(p / 3.0) * 3.0) for p in pred]
    mae_base, mae_model, mae_floor = _mae(y_ho, base), _mae(y_ho, pred), _mae(y_ho, pred_floor)
    within3_base = sum(1 for a, b in zip(y_ho, base, strict=True) if abs(a - b) <= 3.0) / n_hold
    within3_model = sum(1 for a, b in zip(y_ho, pred, strict=True) if abs(a - b) <= 3.0) / n_hold
    within3_floor = (
        sum(1 for a, b in zip(y_ho, pred_floor, strict=True) if abs(a - b) <= 3.0) / n_hold
    )
    importance = sorted(
        zip(names, model.feature_importances_.tolist(), strict=True), key=lambda x: -x[1]
    )
    win = mae_model < mae_base
    report = {
        "holdout": n_hold,
        "mae_baseline_grid_median": round(mae_base, 3),
        "mae_model": round(mae_model, 3),
        "mae_model_rounded_floor": round(mae_floor, 3),
        "within_1_floor_baseline": round(within3_base, 3),
        "within_1_floor_model": round(within3_model, 3),
        "within_1_floor_model_rounded": round(within3_floor, 3),
        "adopt": win,
        "importance": importance,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    print(
        f"\n[홀드아웃 {n_hold:,}동] MAE 격자중앙값 {mae_base:.2f}m vs 모델 {mae_model:.2f}m · "
        f"±1층(3m) 적중 {within3_base:.1%} vs {within3_model:.1%} → {'채택' if win else '미채택'}"
    )
    print(f"[층 반올림 변형] MAE {mae_floor:.2f}m · ±1층 적중 {within3_floor:.1%}")
    print("[importance]", ", ".join(f"{n}={v}" for n, v in importance[:6]))
    _REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    model.booster_.save_model(str(_MODEL_OUT))
    print(f"[out] {_REPORT_OUT.name} · {_MODEL_OUT.name}")

    if args.apply and win and unknown:
        preds = _predict_unknown(args.model, model, rows, names, x_tr, y_tr, unknown, args.seed)
        # 홀드아웃에서 층 단위 반올림이 연속값보다 나았다(MAE 3.59 vs 3.64, ±1층 76.6% vs 64.5%).
        out = {
            str(i): max(3.0, round(min(max(float(p), 3.0), _MAX_H) / 3.0) * 3.0)
            for i, p in zip(unknown, preds, strict=True)
        }
        _PRED_OUT.write_text(json.dumps(out), encoding="utf-8")
        print(f"[apply] 결측 {len(out):,}동 예측 → {_PRED_OUT.name}")
    print(json.dumps({k: v for k, v in report.items() if k != "importance"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
