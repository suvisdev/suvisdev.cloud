"""쿠모니지 게임판 3D 렌더(11-28 사용자: 블렌더로 원근을 맞추고 2D 그림체로 입히기, 48도).

    ~/.local/blender/blender -b -P kumoniji/tools/table3d/render.py -- <출력폴더> [preview]

탁자(table.png)와 세운 패 한 칸씩(wall_<자리>_<칸>.png, 자리 1·2·3 × 13칸)을 같은 카메라로 따로 렌더한다 — 상대
남은 장수가 판마다 바뀌어 한 장으로 굳힐 수 없어서. 같은 카메라로 판 네 모서리·패 칸 위치를 화면 좌표로 table3d.json에
남겨, 앱이 내는 패(판 평면)를 같은 원근으로 그리고 이름을 패 위에 붙인다. 그림은 렌더 뒤 crop.py가 잘라 낸다.
"""
import bpy, json, math, sys
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
preview = len(args) > 1 and args[1] == "preview"
# 시안: 패 앞면 그림(PNG 폴더)을 입혀 낸 패·내 손패까지 한 장에 — 손패 자리만큼 화면을 아래로 늘린다
mock = args[2] if len(args) > 2 and args[1] == "mock" else None
EXTRA = 0
RES = (1688, 780)  # 폰 가로 844×390의 2배 — 탁자가 화면 전체, 앞 가장자리는 내 손패가 덮는다(11-28 사용자가 고른 48도 구도)
TILT = 48  # 수평에서 내려다보는 각(사용자 고름)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16 if preview else 40
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = RES[0], RES[1] + EXTRA
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"


def hexrgb(h):  # sRGB hex → 선형
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)


def mat(name, hex_, rough=.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexrgb(hex_), 1)
    b.inputs["Roughness"].default_value = rough
    return m


felt, rim, base = mat("felt", "E8F0DC", .9), mat("rim", "B8CFA0", .7), mat("base", "A9BC94", .8)
back, side = mat("back", "9CC48E", .5), mat("side", "EADBB8", .5)


def box(name, size, loc, mats, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)  # 기본값은 셋 다 True — 위치까지 원점으로 간다
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width, mod.segments = bevel, 6
    for m in mats:
        o.data.materials.append(m)
    return o


W, D = 2.0, 1.25  # 놀이 자리 폭·깊이(앞이 -y): 패 벽과 낸 패는 이 안에
FW, FD, TOP = W - .06, D - .06, .03  # 놀이 자리 펠트 윗면(앱이 원근 변환에 쓰는 네 모서리)
VW = 4.0  # 보이는 탁자 폭 — 화면 양끝 너머까지 이어지게(11-28 사용자 '양옆에 이어지게')
table = [
    box("base", (VW + .1, D + .1, .10), (0, 0, -.08), [base], .05),
    box("rim", (VW + .06, D + .06, .06), (0, 0, -.005), [rim], .03),
    box("felt", (VW - .06, FD, .02), (0, 0, .02), [felt], .01),
]

TW, TH, TT = .07, .093, .028  # 패 폭·높이·두께
GAP = .004
SIDE_K = 1.0  # 양옆 패 크기 비율
SIDE = TW * SIDE_K + GAP  # 양옆 칸 간격


def slots():
    """(자리, 칸, 놓을 곳, 돌림). 맞은편은 가로로, 양옆은 세로로 13칸 — 칸 0이 먼 쪽(양옆)·왼쪽(맞은편)."""
    for i in range(13):
        yield 2, i, Vector(((i - 6) * (TW + GAP), D / 2 - .09, TOP + TH / 2)), math.pi
    # 양옆은 똑바로 나란히(비스듬히 겹친 판은 11-28 사용자 '이전 버전이 낫다'). 깊이가 모자라 패를 80%로 줄인다
    for seat, sx in ((1, -1), (3, 1)):
        for i in range(13):
            yield seat, i, Vector((sx * (W / 2 - .09), (6 - i) * SIDE + .05, TOP + TH * SIDE_K / 2)), sx * math.pi / 2


def tile(loc, rot, k=1.0):
    o = box("tile", (TW * k, TT * k, TH * k), loc, [side, back], .006)
    for p in o.data.polygons:  # 뒷면(가운데를 보는 면)만 초록
        if p.normal.y > .9:
            p.material_index = 1
    o.rotation_euler = (0, 0, rot)
    return o


bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 32
r, a = 2.35, math.radians(TILT)
cam.location = (0, -r * math.cos(a), r * math.sin(a))
cam.rotation_euler = (math.radians(90 - TILT), 0, 0)
cam.data.shift_y = -.015  # 맞은편 패 벽 위에 이름 자리를 남긴다
cam.data.sensor_fit = "HORIZONTAL"
cam.data.shift_y -= EXTRA / 2 / RES[0]  # 아래로 늘린 만큼 — 게임판 부분은 그대로

bpy.ops.object.light_add(type="AREA", location=(0, -.6, 2.4))
area = bpy.context.object
area.data.energy, area.data.size = 18, 3
bpy.ops.object.light_add(type="SUN", location=(1, -1, 3))
sun = bpy.context.object
sun.data.energy = .9
sun.rotation_euler = (math.radians(35), math.radians(15), 0)
world = bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .55

# 2D 그림체: 외곽선(앱 패·버튼 테두리와 같은 색) + 바닥 그림자만 받는 판
sc.render.use_freestyle = True
sc.render.line_thickness_mode = "ABSOLUTE"
sc.render.line_thickness = 1.6
fs = sc.view_layers[0].freestyle_settings
lset = fs.linesets[0] if fs.linesets else fs.linesets.new("lines")
lset.linestyle = lset.linestyle or bpy.data.linestyles.new("ink")
lset.linestyle.color, lset.linestyle.alpha = hexrgb("5B5368"), .85
nolines = bpy.data.collections.new("nolines")  # 외곽선을 긋지 않을 것: 그림자만 받는 판·그림 속 테두리가 있는 앞면
sc.collection.children.link(nolines)
lset.select_by_collection, lset.collection, lset.collection_negation = True, nolines, "EXCLUSIVE"


def no_lines(o):
    for col in o.users_collection:
        col.objects.unlink(o)
    nolines.objects.link(o)


bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -.13))
floor = bpy.context.object
floor.is_shadow_catcher = True
no_lines(floor)


def px(p):  # 월드 점 → 렌더 화면 픽셀(왼쪽 위 0,0)
    v = world_to_camera_view(sc, cam, Vector(p))
    return [round(v.x * RES[0], 2), round((1 - v.y) * RES[1], 2)]


info = {
    "size": list(RES),
    # 펠트 윗면 네 모서리: 먼 왼쪽·먼 오른쪽·가까운 오른쪽·가까운 왼쪽. 판 좌표(0..1, 0..1, 위가 먼 쪽)와 짝
    "felt": [px((-FW / 2, FD / 2, TOP)), px((FW / 2, FD / 2, TOP)), px((FW / 2, -FD / 2, TOP)), px((-FW / 2, -FD / 2, TOP))],
    "felt_aspect": FD / FW,
    "walls": {},
}


def render(name):
    sc.render.filepath = f"{out}/{name}.png"
    bpy.ops.render.render(write_still=True)


def face(code, loc, rot, w, stand=0.0):
    """패 앞면 그림 한 장(판에 눕히거나 stand°만큼 세움). 그림 아래쪽이 rot 방향의 반대(낸 사람 쪽)를 향한다."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = (w, w * 4 / 3, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    m = bpy.data.materials.new(code)
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(f"{mock}/{code}.png")
    b = nt.nodes["Principled BSDF"]
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = .5
    o.data.materials.append(m)
    o.rotation_euler = (math.radians(stand), 0, rot)
    no_lines(o)  # 그림 안에 테두리가 있다 — 외곽선(투명 여백까지 네모로 두름)에서 뺀다
    return o


if mock:
    for seat, i, loc, rot in slots():
        tile(loc, rot, 1 if seat == 2 else SIDE_K)
    lw, z = .085, TOP + .002
    for k, c in enumerate(["c3", "s4", "l5"]):  # 맞은편이 낸 가장 센 패(자기 앞, 거꾸로)
        face(c, ((1 - k) * (lw + .006), .1, z), math.pi, lw)
    face("c1", (-.55, 0, z), -math.pi / 2, lw)  # 왼쪽 봇: 그림 아래가 왼쪽
    for k, c in enumerate(["m3", "m4"]):
        face(c, (.55, (k - .5) * (lw + .006), z), math.pi / 2, lw)
    face("m9", (0, -.2, z), 0, lw)  # 내 패
    # 내 손패는 그리지 않는다 — 원근을 걸면 가장자리 패가 기울어 보여(11-28 사용자) 앱이 평면으로 그린다
elif preview:  # 구도 보기: 패까지 한 장에
    for seat, i, loc, rot in slots():
        tile(loc, rot, 1 if seat == 2 else SIDE_K)
render("mock" if mock else "table")
if mock:
    sys.exit(0)
if not preview:
    for o in table:  # 패만 그리고 탁자는 감춘다 — 펠트를 그림자 받는 판으로 바꿔 패 그림자는 남긴다
        o.hide_render = True
    catcher = box("felt_catcher", (VW - .06, FD, .02), (0, 0, .02), [felt])
    catcher.is_shadow_catcher = True
    no_lines(catcher)
for seat, i, loc, rot in slots():
    # 앱이 쓰는 점: 패 윗변 가운데(이름을 붙임)·바닥 가운데(내는 패 출발점)
    up = Vector((0, 0, TH * (1 if seat == 2 else SIDE_K) / 2))
    info["walls"].setdefault(str(seat), []).append({"top": px(loc + up), "foot": px(loc - up)})
    if not preview:
        t = tile(loc, rot, 1 if seat == 2 else SIDE_K)
        # 패가 있는 곳만 렌더(화면 전체를 돌리면 한 장에 45초) — 그림자 몫을 넉넉히 둔다. 그림 위치는 그대로(자르지 않음)
        bpy.context.view_layer.update()
        pts = [world_to_camera_view(sc, cam, t.matrix_world @ Vector(c)) for c in t.bound_box]
        sc.render.use_border, sc.render.use_crop_to_border = True, False
        sc.render.border_min_x = max(min(p.x for p in pts) - .03, 0)
        sc.render.border_max_x = min(max(p.x for p in pts) + .03, 1)
        sc.render.border_min_y = max(min(p.y for p in pts) - .08, 0)
        sc.render.border_max_y = min(max(p.y for p in pts) + .03, 1)
        render(f"wall_{seat}_{i}")
        bpy.data.objects.remove(t)
json.dump(info, open(f"{out}/table3d.json", "w"), indent=1)
