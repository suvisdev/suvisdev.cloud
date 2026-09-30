import 'package:flutter_test/flutter_test.dart';
import 'package:gildle/features/gildle/domain/geo_point.dart';
import 'package:gildle/features/gildle/domain/route_guidance.dart';

// 위도 0.001° ≈ 110.5m, 경도 0.001° ≈ 88.3m(위도 37.5°)
const _a = GeoPoint(37.500, 127.000);
const _b = GeoPoint(37.502, 127.000); // 북쪽 221m
const _c = GeoPoint(37.502, 127.002); // 동쪽 177m → 오른쪽으로 꺾임
const _d = GeoPoint(37.500, 127.002); // 남쪽 221m → 오른쪽
final _loop = [_a, _b, _c, _d, _a]; // 서쪽으로 돌아옴 → 오른쪽

void main() {
  test('꺾이는 곳과 방향을 찾는다', () {
    final guide = RouteGuide.build([_a, _b, _c])!;
    expect(guide.turns.length, 1);
    expect(guide.turns.first.side, TurnSide.right);
    expect(guide.turns.first.atM, closeTo(221, 2));
    expect(RouteGuide.build([_c, _b, _a])!.turns.first.side, TurnSide.left);
  });

  test('굽은 길의 잔 꼭짓점은 한 번만 안내한다', () {
    // 90°를 5m 간격 꼭짓점 넷으로 나눠 도는 길
    final guide = RouteGuide.build(const [
      GeoPoint(37.5000, 127.0),
      GeoPoint(37.5010, 127.0),
      GeoPoint(37.50104, 127.00002),
      GeoPoint(37.50107, 127.00006),
      GeoPoint(37.50108, 127.00011),
      GeoPoint(37.50108, 127.0012),
    ])!;
    expect(guide.turns.length, 1);
    expect(guide.turns.first.side, TurnSide.right);
  });

  test('다음 꺾임까지 남은 거리를 알려 준다', () {
    final guide = RouteGuide.build([_a, _b, _c])!;
    final g = guide.locate(const GeoPoint(37.501, 127.0001), 0);
    expect(g.offM, lessThan(12));
    expect(g.next!.distanceM, closeTo(110, 3));
    expect(guidanceText(g, offRoute: false), '110m 앞에서 오른쪽으로');
    final after = guide.locate(const GeoPoint(37.502, 127.001), g.progressM);
    expect(after.next, isNull);
    expect(guidanceText(after, offRoute: false), '도착까지 90m 직진');
  });

  test('돌아오는 코스 — 출발 직후를 도착으로 읽지 않는다', () {
    final guide = RouteGuide.build(_loop)!;
    final g = guide.locate(const GeoPoint(37.5001, 127.0), 0);
    expect(g.progressM, lessThan(30));
    expect(g.remainingM, greaterThan(700));
    // 거의 다 돌아왔을 때는 진행 거리로 도착 쪽을 고른다
    final end = guide.locate(const GeoPoint(37.5, 127.0001), guide.totalM - 60);
    expect(end.remainingM, lessThan(25));
    expect(guidanceText(end, offRoute: false), '거의 다 왔어요');
  });

  test('이탈은 40m에서 켜지고 25m 안으로 와야 꺼진다', () {
    final guide = RouteGuide.build([_a, _b, _c])!;
    final far = guide.locate(const GeoPoint(37.501, 127.0006), 100); // 서→동 53m
    expect(far.offM, closeTo(53, 2));
    expect(isOffRoute(far.offM, wasOff: false), isTrue);
    expect(guidanceText(far, offRoute: true), startsWith('경로에서 53m 벗어났어요'));
    expect(isOffRoute(30, wasOff: false), isFalse);
    expect(isOffRoute(30, wasOff: true), isTrue);
    expect(isOffRoute(20, wasOff: true), isFalse);
  });

  test('질러 가서 다른 구간에 올라서면 그 구간으로 옮긴다', () {
    final guide = RouteGuide.build(_loop)!;
    final g = guide.locate(const GeoPoint(37.501, 127.002), 20); // 세 번째 변 위
    expect(g.offM, lessThan(5));
    expect(g.progressM, closeTo(221 + 177 + 110, 5));
  });
}
