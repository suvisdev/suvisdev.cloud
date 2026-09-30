import 'dart:math' as math;

/// 위경도 한 점. 백엔드 응답의 `[lat, lng]` 배열과 짝이다.
class GeoPoint {
  const GeoPoint(this.lat, this.lng);

  final double lat;
  final double lng;

  factory GeoPoint.fromList(List<dynamic> pair) =>
      GeoPoint((pair[0] as num).toDouble(), (pair[1] as num).toDouble());

  /// 하버사인 거리(m) — 백엔드 `Coordinate.distance_to`와 같은 식.
  double distanceTo(GeoPoint other) {
    const r = 6371000.0;
    final dLat = _rad(other.lat - lat);
    final dLng = _rad(other.lng - lng);
    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_rad(lat)) * math.cos(_rad(other.lat)) * math.sin(dLng / 2) * math.sin(dLng / 2);
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  }

  static double _rad(double deg) => deg * math.pi / 180;
}

/// 진행 방향 화살표 하나 — `from`에서 `to` 쪽으로 향한다.
typedef DirectionArrow = ({GeoPoint from, GeoPoint to});

/// 경로를 따라 일정 간격으로 방향 화살표 자리를 뽑는다(웹 `directionArrows`와 같은 규칙).
/// 돌아오는 코스는 선만 봐서는 어느 쪽으로 도는지 알 수 없어서 넣었다(2026-09-30).
List<DirectionArrow> directionArrows(
  List<GeoPoint> coords, {
  double minGapM = 120,
  int maxCount = 14,
  double headM = 14,
}) {
  final total = polylineLengthM(coords);
  if (total < minGapM) return const [];
  final gap = math.max(minGapM, total / maxCount);
  final arrows = <DirectionArrow>[];
  var walked = 0.0;
  var next = gap / 2;
  for (var i = 1; i < coords.length; i++) {
    final a = coords[i - 1];
    final b = coords[i];
    final len = a.distanceTo(b);
    while (len > 0 && walked + len >= next) {
      final t = (next - walked) / len;
      final t2 = math.min(1.0, t + headM / len);
      if (t2 > t) {
        arrows.add((from: _lerp(a, b, t), to: _lerp(a, b, t2)));
      }
      next += gap;
    }
    walked += len;
  }
  return arrows;
}

GeoPoint _lerp(GeoPoint a, GeoPoint b, double t) =>
    GeoPoint(a.lat + (b.lat - a.lat) * t, a.lng + (b.lng - a.lng) * t);

/// 폴리라인 전체 길이(m).
double polylineLengthM(List<GeoPoint> points) {
  var total = 0.0;
  for (var i = 0; i + 1 < points.length; i++) {
    total += points[i].distanceTo(points[i + 1]);
  }
  return total;
}
