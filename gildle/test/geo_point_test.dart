import 'package:flutter_test/flutter_test.dart';
import 'package:gildle/features/gildle/data/models/route_result.dart';
import 'package:gildle/features/gildle/domain/geo_point.dart';

void main() {
  test('하버사인 거리 — 서울시청↔광화문 약 1.07km', () {
    const cityHall = GeoPoint(37.5663, 126.9779);
    const gwanghwamun = GeoPoint(37.5759, 126.9769);
    final d = cityHall.distanceTo(gwanghwamun);
    expect(d, greaterThan(1000));
    expect(d, lessThan(1150));
  });

  test('폴리라인 길이는 구간 합', () {
    const a = GeoPoint(37.5, 127.0);
    const b = GeoPoint(37.501, 127.0);
    const c = GeoPoint(37.502, 127.0);
    expect(polylineLengthM([a, b, c]), closeTo(2 * a.distanceTo(b), 0.01));
    expect(polylineLengthM([a]), 0);
  });

  test('RouteResult는 여름 필드가 없어도 파싱된다', () {
    final r = RouteResult.fromJson({
      'path': ['N1', 'N2'],
      'coordinates': [
        [37.5, 127.0],
        [37.501, 127.0]
      ],
    });
    expect(r.path.length, 2);
    expect(r.shadeRatio, isNull);
    expect(r.night, isFalse);
    expect(r.isEmpty, isFalse);
  });
}
