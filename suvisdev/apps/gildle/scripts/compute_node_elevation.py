"""보행 그래프 교차점 고도 — SRTM 1초(약 30m) 수치표고에서 쌍선형 보간(2026-09-28).

"편한 길(경사 회피)·언덕길(경사 선호)"과 경로 누적 오르막 계산에 쓴다. 서울은 N37E126·N37E127 두 타일.
타일: AWS 오픈데이터 `s3.amazonaws.com/elevation-tiles-prod/skadi/N37/N37E126.hgt.gz`(gunzip 후 .hgt).
SRTM은 도심 건물 높이가 일부 섞인 표면 모델이라 짧은 간선의 경사는 잡음이 크다 — 사용 측에서 경사를
max(길이, 30m)로 나눠 완화한다.

Usage:
  python scripts/compute_node_elevation.py --hgt-dir /path/to/dem \\
      [--edges data/scored_edges.json] [--out data/node_elevation.json]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

_SIDE = 3601  # SRTM1


def _load_tiles(hgt_dir: Path) -> dict[tuple[int, int], np.ndarray]:
    tiles = {}
    for f in hgt_dir.glob("*.hgt"):
        name = f.stem.upper()  # N37E126
        lat = int(name[1:3]) * (1 if name[0] == "N" else -1)
        lon = int(name[4:7]) * (1 if name[3] == "E" else -1)
        arr = np.fromfile(f, dtype=">i2").reshape((_SIDE, _SIDE)).astype(np.float32)
        arr[arr <= -32768] = np.nan
        tiles[(lat, lon)] = arr
    return tiles


def elevation(tiles: dict[tuple[int, int], np.ndarray], lat: float, lon: float) -> float | None:
    tile = tiles.get((math.floor(lat), math.floor(lon)))
    if tile is None:
        return None
    r = (math.floor(lat) + 1 - lat) * (_SIDE - 1)  # 0행 = 북쪽 끝
    c = (lon - math.floor(lon)) * (_SIDE - 1)
    r0, c0 = int(r), int(c)
    r1, c1 = min(r0 + 1, _SIDE - 1), min(c0 + 1, _SIDE - 1)
    fr, fc = r - r0, c - c0
    v = (
        tile[r0, c0] * (1 - fr) * (1 - fc)
        + tile[r0, c1] * (1 - fr) * fc
        + tile[r1, c0] * fr * (1 - fc)
        + tile[r1, c1] * fr * fc
    )
    return None if math.isnan(v) else round(float(v), 1)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    base = Path(__file__).resolve().parents[1] / "data"
    ap.add_argument("--hgt-dir", type=Path, required=True)
    ap.add_argument("--edges", type=Path, default=base / "scored_edges.json")
    ap.add_argument("--out", type=Path, default=base / "node_elevation.json")
    args = ap.parse_args()

    tiles = _load_tiles(args.hgt_dir)
    rows = json.loads(args.edges.read_text(encoding="utf-8"))
    nodes: dict[str, float] = {}
    for r in rows:
        for nid, la, lo in (
            (r["from_node"], r.get("from_lat"), r.get("from_lng")),
            (r["to_node"], r.get("to_lat"), r.get("to_lng")),
        ):
            if nid in nodes or la is None or lo is None:
                continue
            h = elevation(tiles, la, lo)
            if h is not None:
                nodes[nid] = h
    hs = np.array(list(nodes.values()))
    args.out.write_text(
        json.dumps(
            {"source": "SRTM1 (AWS elevation-tiles-prod skadi)", "nodes": nodes},
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(
        f"노드 {len(nodes)}개 · 고도 {hs.min():.0f}~{hs.max():.0f}m(중앙 {np.median(hs):.0f}m) → {args.out}"
    )


if __name__ == "__main__":
    main()
