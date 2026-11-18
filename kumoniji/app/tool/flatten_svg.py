"""flutter_svg가 못 그리는 SVG 구조를 편다(Codex가 준 패 그림을 앱에 넣기 전에 한 번 돌린다).
<use>→<symbol>·도형 펼치기, 중첩 <svg>→<g transform>, filter 제거, clipPath·그라디언트는 맨 위 <defs>로.
사용: python3 tool/flatten_svg.py 원본폴더 assets/tiles  → 확인은 flutter build web -t tool/sheet_main.dart"""

import copy
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://www.w3.org/2000/svg"
XL = "http://www.w3.org/1999/xlink"
ET.register_namespace("", NS)
ET.register_namespace("xlink", XL)
T = lambda n: f"{{{NS}}}{n}"


def num(v, d=0.0):
    return float(re.sub(r"[a-z%]+$", "", v)) if v not in (None, "") else d


def href(el):
    return el.get("href") or el.get(f"{{{XL}}}href")


def expand(el, ids, depth=0):
    assert depth < 20, "참조 순환"
    for i, ch in enumerate(list(el)):
        if ch.tag == T("use"):
            ref = ids[href(ch).lstrip("#")]
            x, y = num(ch.get("x")), num(ch.get("y"))
            g = ET.Element(T("g"))
            for k, v in ch.attrib.items():
                if k not in (
                    "x",
                    "y",
                    "width",
                    "height",
                    "href",
                    f"{{{XL}}}href",
                    "transform",
                ):
                    g.set(k, v)
            tf = [ch.get("transform", ""), f"translate({x} {y})"]
            if ref.tag == T("symbol"):
                vb = [float(v) for v in re.split(r"[ ,]+", ref.get("viewBox").strip())]
                w, h = num(ch.get("width"), vb[2]), num(ch.get("height"), vb[3])
                par = (
                    ch.get("preserveAspectRatio")
                    or ref.get("preserveAspectRatio")
                    or "xMidYMid meet"
                )
                sx, sy = w / vb[2], h / vb[3]
                if par.strip() != "none":
                    s = min(sx, sy) if "slice" not in par else max(sx, sy)
                    ox = {"xMin": 0, "xMid": 0.5, "xMax": 1}[par[:4]] * (w - vb[2] * s)
                    oy = {"YMin": 0, "YMid": 0.5, "YMax": 1}[par[4:8]] * (h - vb[3] * s)
                    sx = sy = s
                    tf.append(f"translate({ox} {oy})")
                tf.append(f"scale({sx} {sy}) translate({-vb[0]} {-vb[1]})")
                kids = [copy.deepcopy(k) for k in ref]
            else:
                # 도형 하나를 가리키는 <use>는 <g>로 감싸지 않고 그 도형으로 바꾼다(clipPath 안에는 <g>가 올 수 없다)
                el2 = copy.deepcopy(ref)
                el2.attrib.pop("id", None)
                for k, v in g.attrib.items():
                    el2.set(k, v)
                t = " ".join(x for x in tf + [ref.get("transform", "")] if x)
                if t:
                    el2.set("transform", t)
                expand(el2, ids, depth + 1)
                el[i] = el2
                continue
            g.set("transform", " ".join(t for t in tf if t))
            g.extend(kids)
            expand(g, ids, depth + 1)
            el[i] = g
        elif ch.tag == T("svg"):
            # 중첩 <svg>도 flutter_svg가 못 그린다 → viewBox 배치를 계산해 <g transform>으로
            x, y = num(ch.get("x")), num(ch.get("y"))
            tf = [f"translate({x} {y})"]
            if ch.get("viewBox"):
                vb = [float(v) for v in re.split(r"[ ,]+", ch.get("viewBox").strip())]
                w, h = num(ch.get("width"), vb[2]), num(ch.get("height"), vb[3])
                par = ch.get("preserveAspectRatio") or "xMidYMid meet"
                sx, sy = w / vb[2], h / vb[3]
                if par.strip() != "none":
                    sc = min(sx, sy) if "slice" not in par else max(sx, sy)
                    ox = {"xMin": 0, "xMid": 0.5, "xMax": 1}[par[:4]] * (w - vb[2] * sc)
                    oy = {"YMin": 0, "YMid": 0.5, "YMax": 1}[par[4:8]] * (
                        h - vb[3] * sc
                    )
                    sx = sy = sc
                    tf.append(f"translate({ox} {oy})")
                tf.append(f"scale({sx} {sy}) translate({-vb[0]} {-vb[1]})")
            g = ET.Element(T("g"))
            for k, v in ch.attrib.items():
                if k not in (
                    "x",
                    "y",
                    "width",
                    "height",
                    "viewBox",
                    "preserveAspectRatio",
                    "overflow",
                ):
                    g.set(k, v)
            g.set("transform", " ".join(tf))
            g.extend(list(ch))
            expand(g, ids, depth + 1)
            el[i] = g
        else:
            expand(ch, ids, depth)


DEFS = ("clipPath", "linearGradient", "radialGradient", "mask", "pattern")


def drop_defs(el):
    for ch in list(el):
        if ch.tag in tuple(T(d) for d in DEFS):
            el.remove(ch)
        else:
            drop_defs(ch)


def strip(el):
    for ch in list(el):
        if ch.tag in (T("filter"), T("symbol")):
            el.remove(ch)
            continue
        ch.attrib.pop("filter", None)
        strip(ch)


def main(src, dst):
    Path(dst).mkdir(parents=True, exist_ok=True)
    for f in sorted(Path(src).glob("*.svg")):
        if f.name == "sheet.svg":
            continue
        root = ET.parse(f).getroot()
        ids = {e.get("id"): e for e in root.iter() if e.get("id")}
        # clipPath·그라디언트는 symbol을 지우거나 펼쳐 복사하면 사라지거나 id가 겹치므로 모두 맨 위 <defs> 한 곳으로 모은다
        expand(root, ids)
        hoisted = [
            copy.deepcopy(e) for e in root.iter() if e.tag in tuple(T(d) for d in DEFS)
        ]
        strip(root)
        drop_defs(root)
        defs = ET.Element(T("defs"))
        seen = set()
        for e in hoisted:
            if e.get("id") not in seen:
                seen.add(e.get("id"))
                defs.append(e)
        root.insert(0, defs)
        left = [
            e.tag
            for e in root.iter()
            if e.tag in (T("use"), T("symbol"), T("filter"), T("svg")) and e is not root
        ]
        assert not left, (f.name, left)
        ET.ElementTree(root).write(Path(dst) / f.name, encoding="unicode")
    print("ok", len(list(Path(dst).glob("*.svg"))))


if __name__ == "__main__":
    main(*sys.argv[1:3])
