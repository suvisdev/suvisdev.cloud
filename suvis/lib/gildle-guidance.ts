/** 길들 산책 중 길 안내 — 앱 `gildle/lib/features/gildle/domain/route_guidance.dart`와 같은 규칙
 *  (2026-09-30). 한쪽을 바꾸면 다른 쪽도 같이 바꾼다. 백엔드 호출 없이 경로 좌표만으로 계산한다. */

export type GuidePoint = { lat: number; lng: number }
export type TurnSide = "left" | "right" | "back"
export type Turn = { atM: number; side: TurnSide }
export type RouteGuide = { coords: GuidePoint[]; cum: number[]; totalM: number; turns: Turn[] }
export type Guidance = {
  /** 경로를 따라 온 거리 */
  progressM: number
  /** 경로에서 떨어진 거리 */
  offM: number
  remainingM: number
  next: { distanceM: number; side: TurnSide } | null
}

const TURN_LOOK_M = 15 // 꺾임을 잴 때 앞뒤로 보는 거리
const TURN_MIN_DEG = 40
const TURN_BACK_DEG = 150
const TURN_MERGE_M = 30 // 이 안의 꺾임들은 하나로(굽은 길의 잔 꼭짓점)
const WINDOW_BACK_M = 30
const WINDOW_AHEAD_M = 250
const OFF_ENTER_M = 40 // 이만큼 벗어나면 이탈
const OFF_EXIT_M = 25 // 이 안으로 돌아오면 복귀(경계에서 깜빡이지 않게 차이를 둔다)
const SOON_M = 25
const LOOP_GAP_M = 50 // 시작·끝이 이 안이면 돌아오는 코스
const REJOIN_AHEAD_M = 400 // 합류 지점은 이 앞까지만 찾는다(출발점 근처에서 끝점으로 건너뛰지 않게)

const M_PER_DEG_LAT = 110540
const M_PER_DEG_LNG = 111320

function toXY(p: GuidePoint, origin: GuidePoint): [number, number] {
  return [
    (p.lng - origin.lng) * M_PER_DEG_LNG * Math.cos((origin.lat * Math.PI) / 180),
    (p.lat - origin.lat) * M_PER_DEG_LAT,
  ]
}

function distM(a: GuidePoint, b: GuidePoint): number {
  const [x, y] = toXY(b, a)
  return Math.hypot(x, y)
}

/** 북 0°, 시계 방향. */
function bearing(a: GuidePoint, b: GuidePoint): number {
  const [x, y] = toXY(b, a)
  return ((Math.atan2(x, y) * 180) / Math.PI + 360) % 360
}

function pointAt(coords: GuidePoint[], cum: number[], alongM: number): GuidePoint {
  const m = Math.max(0, Math.min(cum[cum.length - 1], alongM))
  for (let i = 1; i < coords.length; i++) {
    if (cum[i] >= m) {
      const len = cum[i] - cum[i - 1]
      const t = len > 0 ? (m - cum[i - 1]) / len : 0
      const a = coords[i - 1]
      const b = coords[i]
      return { lat: a.lat + (b.lat - a.lat) * t, lng: a.lng + (b.lng - a.lng) * t }
    }
  }
  return coords[coords.length - 1]
}

export function buildGuide(coords: GuidePoint[]): RouteGuide | null {
  if (coords.length < 2) return null
  const cum = [0]
  for (let i = 1; i < coords.length; i++) cum.push(cum[i - 1] + distM(coords[i - 1], coords[i]))
  const totalM = cum[cum.length - 1]
  const turns: (Turn & { deg: number })[] = []
  for (let i = 1; i < coords.length - 1; i++) {
    const before = pointAt(coords, cum, cum[i] - TURN_LOOK_M)
    const after = pointAt(coords, cum, cum[i] + TURN_LOOK_M)
    if (distM(before, coords[i]) < 1 || distM(coords[i], after) < 1) continue
    const delta = ((bearing(coords[i], after) - bearing(before, coords[i]) + 540) % 360) - 180
    const deg = Math.abs(delta)
    if (deg < TURN_MIN_DEG) continue
    const turn = {
      atM: cum[i],
      side: (deg >= TURN_BACK_DEG ? "back" : delta > 0 ? "right" : "left") as TurnSide,
      deg,
    }
    const last = turns[turns.length - 1]
    if (last && turn.atM - last.atM < TURN_MERGE_M) {
      if (deg > last.deg) turns[turns.length - 1] = turn
    } else {
      turns.push(turn)
    }
  }
  return { coords, cum, totalM, turns: turns.map(({ atM, side }) => ({ atM, side })) }
}

/** 지금 위치가 경로의 어디쯤인지. `prevProgressM` 근처를 먼저 본다 — 돌아오는 코스는 출발점과
 *  도착점이 겹쳐서, 가장 가까운 구간만 찾으면 출발하자마자 '도착'으로 읽힌다. */
export function locate(guide: RouteGuide, p: GuidePoint, prevProgressM: number): Guidance {
  const { coords, cum, totalM, turns } = guide
  type Hit = { off: number; along: number }
  let near: Hit | null = null
  let nearest: Hit = { off: Infinity, along: 0 }
  for (let i = 1; i < coords.length; i++) {
    const [ax, ay] = toXY(coords[i - 1], p)
    const [bx, by] = toXY(coords[i], p)
    const dx = bx - ax
    const dy = by - ay
    const len2 = dx * dx + dy * dy
    const t = len2 > 0 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2)) : 0
    const off = Math.hypot(ax + dx * t, ay + dy * t)
    const along = cum[i - 1] + (cum[i] - cum[i - 1]) * t
    if (off < nearest.off) nearest = { off, along }
    const inWindow =
      cum[i] >= prevProgressM - WINDOW_BACK_M && cum[i - 1] <= prevProgressM + WINDOW_AHEAD_M
    if (inWindow && (!near || off < near.off)) near = { off, along }
  }
  // 근처에서 못 찾았는데 다른 구간 위에 있으면(질러 갔거나 중간에서 시작) 그쪽으로 옮긴다
  let best = near ?? nearest
  if (best.off > OFF_ENTER_M && nearest.off <= OFF_EXIT_M) best = nearest
  const turn = turns.find((t) => t.atM > best.along + 1)
  return {
    progressM: best.along,
    offM: best.off,
    remainingM: totalM - best.along,
    next: turn ? { distanceM: turn.atM - best.along, side: turn.side } : null,
  }
}

/** 시작과 끝이 같은 자리면 돌아오는 코스. */
export function isLoopRoute(coords: GuidePoint[]): boolean {
  return coords.length >= 2 && distM(coords[0], coords[coords.length - 1]) < LOOP_GAP_M
}

/** 이탈했을 때 새 길이 향할 곳. 목적지가 있는 길은 끝점, 돌아오는 코스는 아직 안 걸은 구간에서
 *  가장 가까운 지점 — 거기로 합류해 나머지는 원래 코스를 그대로 걷는다. */
export function rejoinTarget(
  guide: RouteGuide,
  p: GuidePoint,
  progressM: number
): { point: GuidePoint; alongM: number } {
  const { coords, cum, totalM } = guide
  if (!isLoopRoute(coords)) return { point: coords[coords.length - 1], alongM: totalM }
  const from = Math.min(progressM, totalM)
  const to = Math.min(totalM, from + REJOIN_AHEAD_M)
  let best = { off: Infinity, along: from }
  for (let i = 1; i < coords.length; i++) {
    const len = cum[i] - cum[i - 1]
    if (cum[i] < from || cum[i - 1] > to || len <= 0) continue
    const [ax, ay] = toXY(coords[i - 1], p)
    const [bx, by] = toXY(coords[i], p)
    const dx = bx - ax
    const dy = by - ay
    // 구간 중 [from, to]에 드는 부분으로만 투영한다
    const tMin = Math.max(0, (from - cum[i - 1]) / len)
    const tMax = Math.min(1, (to - cum[i - 1]) / len)
    const t = Math.max(tMin, Math.min(tMax, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    const off = Math.hypot(ax + dx * t, ay + dy * t)
    if (off < best.off) best = { off, along: cum[i - 1] + len * t }
  }
  return { point: pointAt(coords, cum, best.along), alongM: best.along }
}

/** `alongM` 지점부터 끝까지의 원래 경로. */
export function remainderFrom(guide: RouteGuide, alongM: number): GuidePoint[] {
  const { coords, cum } = guide
  return [pointAt(coords, cum, alongM), ...coords.filter((_, i) => cum[i] > alongM)]
}

export function isOffRoute(offM: number, wasOff: boolean): boolean {
  return offM > (wasOff ? OFF_EXIT_M : OFF_ENTER_M)
}

const SIDE_LABEL: Record<TurnSide, string> = {
  left: "왼쪽으로",
  right: "오른쪽으로",
  back: "되돌아가기",
}

/** 안내 한 줄 — "120m 앞에서 왼쪽으로". */
export function guidanceText(g: Guidance, offRoute: boolean): string {
  if (offRoute) return `경로에서 ${Math.round(g.offM)}m 벗어났어요`
  if (g.remainingM < SOON_M) return "거의 다 왔어요"
  if (!g.next) return `도착까지 ${Math.round(g.remainingM / 10) * 10}m 직진`
  const side = SIDE_LABEL[g.next.side]
  if (g.next.distanceM < SOON_M) return `곧 ${side}`
  return `${Math.round(g.next.distanceM / 10) * 10}m 앞에서 ${side}`
}
