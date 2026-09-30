import 'package:flutter_test/flutter_test.dart';
import 'package:gildle/features/gildle/data/models/route_option.dart';
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

  test('RouteOption은 선택 필드가 없어도 파싱된다', () {
    final o = RouteOption.fromJson({
      'kind': 'fast',
      'label': '빠른 길',
      'length_m': 659.8,
      'coordinates': [
        [37.5, 127.0],
        [37.501, 127.0]
      ],
    });
    expect(o.coordinates.length, 2);
    expect(o.shadeRatio, isNull);
    expect(o.recommended, isFalse);
    expect(o.places, isEmpty);
  });

  test('WalkPlan — 목적지가 있는 추천은 출발지로 돌아오지 않는다', () {
    final plan = WalkPlan.fromJson({
      'understood': {
        'kind': 'route',
        'minutes': null,
        'distance_km': null,
        'preference': 'fast',
        'stops': <String>[],
        'destination': '동물병원',
        'source': 'llm',
      },
      'destination_place': {'name': '서울동물병원', 'category': '동물병원', 'lat': 37.526, 'lng': 126.918, 'address': ''},
      'via_place': null,
      'target_m': 2052,
      'options': <Map<String, dynamic>>[],
      'night': false,
    });
    expect(plan.returnsToStart, isFalse);
    expect(plan.destination?.lat, 37.526);
    expect(plan.destinationName, '서울동물병원');
  });
}
