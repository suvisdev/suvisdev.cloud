import 'dart:math' as math;

import 'geo_point.dart';

/// 산책 중 길 안내 — 웹 `suvis/lib/gildle-guidance.ts`와 같은 규칙(2026-09-30).
/// 한쪽을 바꾸면 다른 쪽도 같이 바꾼다. 백엔드 호출 없이 경로 좌표만으로 계산한다.

enum TurnSide { left, right, back }

typedef Turn = ({double atM, TurnSide side});

class Guidance {
  const Guidance({required this.progressM, required this.offM, required this.remainingM, this.next});

  /// 경로를 따라 온 거리
  final double progressM;

  /// 경로에서 떨어진 거리
  final double offM;
  final double remainingM;
  final ({double distanceM, TurnSide side})? next;
}

const _turnLookM = 15.0; // 꺾임을 잴 때 앞뒤로 보는 거리
const _turnMinDeg = 40.0;
const _turnBackDeg = 150.0;
const _turnMergeM = 30.0; // 이 안의 꺾임들은 하나로(굽은 길의 잔 꼭짓점)
const _windowBackM = 30.0;
const _windowAheadM = 250.0;
const _offEnterM = 40.0; // 이만큼 벗어나면 이탈
const _offExitM = 25.0; // 이 안으로 돌아오면 복귀(경계에서 깜빡이지 않게 차이를 둔다)
const _soonM = 25.0;
const _loopGapM = 50.0; // 시작·끝이 이 안이면 돌아오는 코스
const _rejoinAheadM = 400.0; // 합류 지점은 이 앞까지만 찾는다(출발점 근처에서 끝점으로 건너뛰지 않게)

const _mPerDegLat = 110540.0;
const _mPerDegLng = 111320.0;

(double, double) _toXY(GeoPoint p, GeoPoint origin) => (
      (p.lng - origin.lng) * _mPerDegLng * math.cos(origin.lat * math.pi / 180),
      (p.lat - origin.lat) * _mPerDegLat,
    );

double _distM(GeoPoint a, GeoPoint b) {
  final (x, y) = _toXY(b, a);
  return math.sqrt(x * x + y * y);
}

/// 북 0°, 시계 방향.
double _bearing(GeoPoint a, GeoPoint b) {
  final (x, y) = _toXY(b, a);
  return (math.atan2(x, y) * 180 / math.pi + 360) % 360;
}

class RouteGuide {
  RouteGuide._(this.coords, this.cum, this.turns);

  final List<GeoPoint> coords;
  final List<double> cum;
  final List<Turn> turns;

  double get totalM => cum.last;

  /// 시작과 끝이 같은 자리면 돌아오는 코스.
  bool get isLoop => _distM(coords.first, coords.last) < _loopGapM;

  /// 이탈했을 때 새 길이 향할 곳. 목적지가 있는 길은 끝점, 돌아오는 코스는 아직 안 걸은 구간에서
  /// 가장 가까운 지점 — 거기로 합류해 나머지는 원래 코스를 그대로 걷는다.
  ({GeoPoint point, double alongM}) rejoinTarget(GeoPoint p, double progressM) {
    if (!isLoop) return (point: coords.last, alongM: totalM);
    final from = math.min(progressM, totalM);
    final to = math.min(totalM, from + _rejoinAheadM);
    var bestOff = double.infinity;
    var bestAlong = from;
    for (var i = 1; i < coords.length; i++) {
      final len = cum[i] - cum[i - 1];
      if (cum[i] < from || cum[i - 1] > to || len <= 0) continue;
      final (ax, ay) = _toXY(coords[i - 1], p);
      final (bx, by) = _toXY(coords[i], p);
      final dx = bx - ax;
      final dy = by - ay;
      // 구간 중 [from, to]에 드는 부분으로만 투영한다
      final tMin = math.max(0.0, (from - cum[i - 1]) / len);
      final tMax = math.min(1.0, (to - cum[i - 1]) / len);
      final t = (-(ax * dx + ay * dy) / (dx * dx + dy * dy)).clamp(tMin, tMax);
      final ox = ax + dx * t;
      final oy = ay + dy * t;
      final off = math.sqrt(ox * ox + oy * oy);
      if (off < bestOff) {
        bestOff = off;
        bestAlong = cum[i - 1] + len * t;
      }
    }
    return (point: _pointAt(coords, cum, bestAlong), alongM: bestAlong);
  }

  /// [alongM] 지점부터 끝까지의 원래 경로.
  List<GeoPoint> remainderFrom(double alongM) => [
        _pointAt(coords, cum, alongM),
        for (var i = 0; i < coords.length; i++)
          if (cum[i] > alongM) coords[i],
      ];

  static RouteGuide? build(List<GeoPoint> coords) {
    if (coords.length < 2) return null;
    final cum = <double>[0];
    for (var i = 1; i < coords.length; i++) {
      cum.add(cum[i - 1] + _distM(coords[i - 1], coords[i]));
    }
    final turns = <Turn>[];
    final degs = <double>[];
    for (var i = 1; i < coords.length - 1; i++) {
      final before = _pointAt(coords, cum, cum[i] - _turnLookM);
      final after = _pointAt(coords, cum, cum[i] + _turnLookM);
      if (_distM(before, coords[i]) < 1 || _distM(coords[i], after) < 1) continue;
      final delta = ((_bearing(coords[i], after) - _bearing(before, coords[i]) + 540) % 360) - 180;
      final deg = delta.abs();
      if (deg < _turnMinDeg) continue;
      final Turn turn = (
        atM: cum[i],
        side: deg >= _turnBackDeg ? TurnSide.back : (delta > 0 ? TurnSide.right : TurnSide.left),
      );
      if (turns.isNotEmpty && turn.atM - turns.last.atM < _turnMergeM) {
        if (deg > degs.last) {
          turns[turns.length - 1] = turn;
          degs[degs.length - 1] = deg;
        }
      } else {
        turns.add(turn);
        degs.add(deg);
      }
    }
    return RouteGuide._(coords, cum, turns);
  }

  /// 지금 위치가 경로의 어디쯤인지. [prevProgressM] 근처를 먼저 본다 — 돌아오는 코스는 출발점과
  /// 도착점이 겹쳐서, 가장 가까운 구간만 찾으면 출발하자마자 '도착'으로 읽힌다.
  Guidance locate(GeoPoint p, double prevProgressM) {
    ({double off, double along})? near;
    ({double off, double along})? any;
    for (var i = 1; i < coords.length; i++) {
      final (ax, ay) = _toXY(coords[i - 1], p);
      final (bx, by) = _toXY(coords[i], p);
      final dx = bx - ax;
      final dy = by - ay;
      final len2 = dx * dx + dy * dy;
      final t = len2 > 0 ? (-(ax * dx + ay * dy) / len2).clamp(0.0, 1.0) : 0.0;
      final ox = ax + dx * t;
      final oy = ay + dy * t;
      final off = math.sqrt(ox * ox + oy * oy);
      final along = cum[i - 1] + (cum[i] - cum[i - 1]) * t;
      if (any == null || off < any.off) any = (off: off, along: along);
      final inWindow = cum[i] >= prevProgressM - _windowBackM && cum[i - 1] <= prevProgressM + _windowAheadM;
      if (inWindow && (near == null || off < near.off)) near = (off: off, along: along);
    }
    // 근처에서 못 찾았는데 다른 구간 위에 있으면(질러 갔거나 중간에서 시작) 그쪽으로 옮긴다
    final best = near != null && near.off <= _offEnterM
        ? near
        : (any!.off <= _offExitM ? any : (near ?? any));
    Turn? turn;
    for (final t in turns) {
      if (t.atM > best.along + 1) {
        turn = t;
        break;
      }
    }
    return Guidance(
      progressM: best.along,
      offM: best.off,
      remainingM: totalM - best.along,
      next: turn == null ? null : (distanceM: turn.atM - best.along, side: turn.side),
    );
  }
}

GeoPoint _pointAt(List<GeoPoint> coords, List<double> cum, double alongM) {
  final m = alongM.clamp(0.0, cum.last);
  for (var i = 1; i < coords.length; i++) {
    if (cum[i] >= m) {
      final len = cum[i] - cum[i - 1];
      final t = len > 0 ? (m - cum[i - 1]) / len : 0.0;
      final a = coords[i - 1];
      final b = coords[i];
      return GeoPoint(a.lat + (b.lat - a.lat) * t, a.lng + (b.lng - a.lng) * t);
    }
  }
  return coords.last;
}

bool isOffRoute(double offM, {required bool wasOff}) => offM > (wasOff ? _offExitM : _offEnterM);

const _sideLabels = {
  TurnSide.left: '왼쪽으로',
  TurnSide.right: '오른쪽으로',
  TurnSide.back: '되돌아가기',
};

/// 안내 한 줄 — "120m 앞에서 왼쪽으로".
String guidanceText(Guidance g, {required bool offRoute}) {
  if (offRoute) return '경로에서 ${g.offM.round()}m 벗어났어요';
  if (g.remainingM < _soonM) return '거의 다 왔어요';
  final next = g.next;
  if (next == null) return '도착까지 ${(g.remainingM / 10).round() * 10}m 직진';
  final side = _sideLabels[next.side]!;
  if (next.distanceM < _soonM) return '곧 $side';
  return '${(next.distanceM / 10).round() * 10}m 앞에서 $side';
}
