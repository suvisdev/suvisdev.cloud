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

/// 폴리라인 전체 길이(m).
double polylineLengthM(List<GeoPoint> points) {
  var total = 0.0;
  for (var i = 0; i + 1 < points.length; i++) {
    total += points[i].distanceTo(points[i + 1]);
  }
  return total;
}
