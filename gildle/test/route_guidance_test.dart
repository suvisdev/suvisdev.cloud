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
    expect(guidanceText(far, offRoute: true), '경로에서 53m 벗어났어요');
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

  test('다시 찾기 — 목적지가 있는 길은 끝점으로', () {
    final guide = RouteGuide.build([_a, _b, _c])!;
    expect(guide.isLoop, isFalse);
    final t = guide.rejoinTarget(const GeoPoint(37.501, 127.0006), 100);
    expect(t.point.lat, _c.lat);
    expect(t.alongM, closeTo(guide.totalM, 0.01));
    expect(guide.remainderFrom(t.alongM).length, 1);
  });

  test('다시 찾기 — 돌아오는 코스는 아직 안 걸은 구간의 가까운 지점으로 합류', () {
    final guide = RouteGuide.build(_loop)!;
    expect(guide.isLoop, isTrue);
    // 첫 변을 150m쯤 걷다 동쪽으로 60m 벗어남 → 첫 변의 같은 높이로 합류
    final t = guide.rejoinTarget(const GeoPoint(37.5014, 127.0007), 150);
    expect(t.alongM, closeTo(155, 3));
    final rest = guide.remainderFrom(t.alongM);
    expect(rest.first.lat, closeTo(37.5014, 0.0001));
    expect(rest.last.lat, _a.lat); // 끝은 출발지
    expect(rest.length, 5); // 합류점 + b·c·d·a
    // 이미 지나온 구간으로는 되돌리지 않는다
    final ahead = guide.rejoinTarget(const GeoPoint(37.5005, 127.0007), 150);
    expect(ahead.alongM, greaterThanOrEqualTo(150));
  });

  test('다시 찾기 — 출발 직후엔 코스를 건너뛰어 끝점으로 합류하지 않는다', () {
    final guide = RouteGuide.build(_loop)!;
    // 출발점에서 동쪽 60m: 마지막 변(서쪽으로 돌아오는 길) 바로 위지만 400m 앞까지만 본다
    final t = guide.rejoinTarget(const GeoPoint(37.5, 127.0007), 10);
    expect(t.alongM, lessThan(420));
  });

  // 경로를 따라 약 5m 간격으로 걸으며 나온 음성 안내를 모은다
  List<String> walk(List<GeoPoint> route, List<GeoPoint> path) {
    final guide = RouteGuide.build(route)!;
    final spoken = <String>{};
    final said = <String>[];
    var progress = 0.0;
    for (final p in path) {
      final g = guide.locate(p, progress);
      progress = g.progressM;
      final cue = nextCue(g, offRoute: false, spoken: spoken);
      if (cue != null) {
        spoken.add(cue.key);
        said.add(cue.text);
      }
    }
    return said;
  }

  List<GeoPoint> along(GeoPoint from, GeoPoint to, int steps) => [
        for (var i = 0; i <= steps; i++)
          GeoPoint(from.lat + (to.lat - from.lat) * i / steps, from.lng + (to.lng - from.lng) * i / steps),
      ];

  test('음성 안내 — 꺾임마다 앞에서 한 번·직전에 한 번, 끝에서 도착', () {
    final said = walk([_a, _b, _c], [...along(_a, _b, 40), ...along(_b, _c, 32)]);
    expect(said, ['60미터 앞에서 오른쪽으로 가세요', '곧 오른쪽으로 가세요', '도착했어요']);
  });

  test('음성 안내 — 돌아오는 코스는 출발 직후 도착이라 말하지 않는다', () {
    final said = walk(_loop, along(_a, _b, 10).take(3).toList());
    expect(said, isEmpty);
  });

  test('음성 안내 — 이탈 중엔 말하지 않는다', () {
    final guide = RouteGuide.build([_a, _b, _c])!;
    final g = guide.locate(const GeoPoint(37.5016, 127.0), 0);
    expect(nextCue(g, offRoute: true, spoken: {}), isNull);
    expect(nextCue(g, offRoute: false, spoken: {})!.text, '40미터 앞에서 오른쪽으로 가세요');
  });
}
