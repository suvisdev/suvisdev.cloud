"""render.py 결과를 앱 자산으로: 세운 패 그림은 투명한 빈 곳을 잘라 내고 화면 위치(렌더 픽셀)를 table3d.json에 적는다.

    uv run --no-project --with pillow python3 kumoniji/tools/table3d/crop.py <렌더폴더> kumoniji/app/assets/table3d \
        kumoniji/app/lib/table3d_data.dart

좌표는 앱이 그림을 불러오기 전에 바로 쓰도록 Dart 상수 파일로 쓴다(JSON은 비동기로만 읽힌다).
"""
import json
import sys
from pathlib import Path

from PIL import Image

src, dst, dart = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
dst.mkdir(parents=True, exist_ok=True)
info = json.loads((src / "table3d.json").read_text())
Image.open(src / "table.png").save(dst / "table.png", optimize=True)
for seat, cells in info["walls"].items():
    for i, cell in enumerate(cells):
        im = Image.open(src / f"wall_{seat}_{i}.png")
        box = im.getchannel("A").point(lambda a: 255 if a > 4 else 0).getbbox()
        im.crop(box).save(dst / f"wall_{seat}_{i}.png", optimize=True)
        cell["rect"] = [box[0], box[1], box[2] - box[0], box[3] - box[1]]
pt = lambda p: f"Offset({p[0]}, {p[1]})"  # noqa: E731
walls = ",\n".join(
    "  [\n" + "".join(f"    T3Slot({pt(c['top'])}, {pt(c['foot'])}, Rect.fromLTWH({', '.join(map(str, c['rect']))})),\n"
                       for c in info["walls"][s]) + "  ]" for s in ("1", "2", "3"))
dart.write_text(f"""// 생성됨: kumoniji/tools/table3d/crop.py — 손으로 고치지 않는다. 렌더 그림(assets/table3d/) 픽셀 좌표.
import 'dart:ui';

/// 세운 패 한 칸: 윗변 가운데·바닥 가운데(판 위 점)·그림 자리
class T3Slot {{
  const T3Slot(this.top, this.foot, this.rect);
  final Offset top, foot;
  final Rect rect;
}}

const t3Size = Size({info['size'][0]}, {info['size'][1]});

/// 펠트 윗면 네 모서리: 먼 왼쪽·먼 오른쪽·가까운 오른쪽·가까운 왼쪽
const t3Felt = [{', '.join(pt(p) for p in info['felt'])}];

/// 펠트 깊이 / 폭(실제 탁자 비율)
const t3FeltAspect = {info['felt_aspect']};

/// 자리 1·2·3의 13칸(자리 1·3은 칸 0이 먼 쪽, 자리 2는 왼쪽부터)
const t3Walls = [
{walls},
];
""")
print("ok", sum(f.stat().st_size for f in dst.iterdir()) // 1024, "KB")
