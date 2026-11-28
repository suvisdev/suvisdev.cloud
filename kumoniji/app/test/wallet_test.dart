import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/auth.dart';
import 'package:kumoniji/auth_screens.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/table_screen.dart';
import 'package:kumoniji/tile.dart';
import 'package:kumoniji/wallet.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;
import 'table_screen_test.dart' show settle;

Widget _wrap(Widget child) => MaterialApp(
  locale: const Locale('en'),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: child,
);

var _clock = 0; // 가짜 서버 시각 — 지금 시각에서 응답을 만들 때마다 조금씩 커진다(서버가 잠금 순서대로 찍는 v처럼)

Map<String, dynamic> wallet({
  double? v,
  double? t,
  String? day,
  bool next7 = false,
  int coins = 0,
  int gems = 0,
  int hearts = 10,
  double? next,
  bool claimed = false,
  List<String> done = const [],
  Map<String, int> counts = const {},
}) {
  final real = DateTime.now().millisecondsSinceEpoch / 1000;
  final at = v ?? real + (++_clock) / 1000;
  final ts = t ?? real;
  return {
    'v': at,
    'now': ts,
    'coins': coins,
    'gems': gems,
    'hearts': hearts,
    'next_heart': next,
    'attend': {
      'day': day ?? kstDay((ts * 1000).round()),
      'streak': claimed ? 1 : 0,
      'claimed': claimed,
      'next': next7 ? 7 : 1,
    },
    'missions': {'all': missionNeed.keys.toList(), 'done': done, 'counts': counts, 'bonus': done.length >= 5},
  };
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    markTilesReady();
    Wallet.current.value = null;
    PendingIds.buy.clear();
    PendingIds.newGame.clear();
    Auth.me.value = null;
  });

  testWidgets('잔고 막대가 골드·햇살·무지개 조각을 보여 주고, 출석하면 늘어난 골드로 바뀐다', (t) async {
    final semantics = t.ensureSemantics();
    var coins = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/attend') coins += 200;
        return http.Response(jsonEncode(wallet(coins: coins, gems: 3, hearts: 7, claimed: coins > 0)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    expect(find.bySemanticsLabel('Gold 0'), findsOneWidget);
    expect(find.bySemanticsLabel('Sunbeams 7'), findsOneWidget);
    expect(find.bySemanticsLabel('Rainbow shards 3'), findsOneWidget);
    await t.tap(find.byKey(const ValueKey('attend')));
    await t.pumpAndSettle();
    expect(find.bySemanticsLabel('Gold 200'), findsOneWidget);
    expect(t.widget<FilledButton>(find.byKey(const ValueKey('attend'))).onPressed, isNull); // 하루 한 번
    semantics.dispose();
  });

  testWidgets('햇살은 5칸 — 가진 만큼 채우고 넘친 몫은 +N, 골드는 천 단위 콤마 숫자 그림', (t) async {
    Iterable<String> suns() => t
        .widgetList<Image>(
          find.descendant(of: find.byKey(const ValueKey('wallet-hearts')), matching: find.byType(Image)),
        )
        .map((i) => (i.image as AssetImage).assetName)
        .where((n) => n.contains('/sun'));
    for (final (hearts, filled, plus) in [(3, 3, null), (7, 5, '+2'), (0, 0, null)]) {
      Auth.client = AuthClient(
        MockClient((_) async => http.Response(jsonEncode(wallet(coins: 12345, hearts: hearts)), 200)),
      );
      Wallet.current.value = null;
      await t.pumpWidget(_wrap(Scaffold(key: UniqueKey(), body: const WalletBar())));
      await Wallet.refresh();
      await t.pumpAndSettle();
      expect(suns(), hasLength(5));
      expect(suns().where((n) => n.endsWith('/sun.png')), hasLength(filled), reason: '$hearts');
      expect(
        find.byWidgetPredicate((w) => w is Digits && w.text == plus),
        plus == null ? findsNothing : findsOneWidget,
      );
      expect(find.byWidgetPredicate((w) => w is Digits && w.text == '12,345'), findsOneWidget);
    }
  });

  testWidgets('잔고 막대의 재화를 누르면 그 탭으로 상점이 열리고, 상점 안에서는 탭만 바뀐다', (t) async {
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(gems: 3)), 200)));
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('wallet-gems')));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('gem-pack-12')), findsOneWidget);
    // 현금 묶음은 아직 못 산다(결제는 문의 뒤)
    expect(
      t
          .widget<OutlinedButton>(
            find.descendant(of: find.byKey(const ValueKey('gem-pack-12')), matching: find.byType(OutlinedButton)),
          )
          .onPressed,
      isNull,
    );
    await t.tap(find.descendant(of: find.byType(AppBar), matching: find.byKey(const ValueKey('wallet-hearts'))));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('buy-hearts15')), findsOneWidget);
    expect(find.byType(ShopScreen), findsOneWidget); // 상점을 또 쌓지 않음
  });

  testWidgets('화면 읽기(TalkBack·VoiceOver)로 잔고 버튼을 두 번 눌러도 상점이 열린다(리뷰 18차)', (t) async {
    final sem = t.ensureSemantics();
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(gems: 3)), 200)));
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    final node = t.getSemantics(find.byKey(const ValueKey('wallet-gems')));
    expect(node.getSemanticsData().hasAction(SemanticsAction.tap), isTrue);
    t.semantics.tap(find.semantics.byLabel(RegExp('^${node.label}\$')));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('gem-pack-12')), findsOneWidget);
    sem.dispose();
  });

  testWidgets('미션은 진행 수/목표와 완료 표시를 보여 준다', (t) async {
    Auth.client = AuthClient(
      MockClient((_) async => http.Response(jsonEncode(wallet(done: ['games5'], counts: {'games': 7})), 200)),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    expect(
      find.descendant(of: find.byKey(const ValueKey('mission-games5')), matching: find.text('5/5')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: find.byKey(const ValueKey('mission-games10')), matching: find.text('7/10')),
      findsOneWidget,
    );
    expect(find.text('Today 1/10 — finish 5 for +300'), findsOneWidget);
  });

  testWidgets('상점: 보석이 모자라면 못 사고, 응답이 끊기면 같은 요청 id로 다시 산다', (t) async {
    final rids = <String>[];
    var fail = true;
    var gems = 10;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/buy') {
          rids.add(jsonDecode(r.body)['rid']);
          if (fail) {
            fail = false;
            return http.Response('', 503);
          }
          gems -= 10;
        }
        return http.Response(jsonEncode(wallet(gems: gems)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pumpAndSettle();
    expect(rids.length, 2);
    expect(rids[0], rids[1]); // 실패 뒤 다시 누르면 같은 id — 서버가 두 번 팔지 않는다
    expect(t.widget<FilledButton>(find.byKey(const ValueKey('buy-hearts5'))).onPressed, isNull); // 보석 0
  });

  test('새 판은 응답을 못 받으면 같은 요청 id로 다시 보낸다', () async {
    final rids = <String>[];
    final api = Api(
      MockClient((r) async {
        rids.add(jsonDecode(r.body)['rid']);
        return rids.length == 1 ? http.Response('', 502) : http.Response(jsonEncode(view()), 200);
      }),
    );
    final g = await api.newGame('easy');
    expect(g.id, 'a');
    expect(rids.length, 2);
    expect(rids[0], rids[1]);
    expect(rids[0], matches(RegExp(r'^[A-Za-z0-9_-]{8,64}$')));
  });

  testWidgets('하트가 없으면(402) 다음 하트까지 남은 시간을 알려 준다', (t) async {
    final next = DateTime.now().millisecondsSinceEpoch / 1000 + 4 * 60 + 10;
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(hearts: 0, next: next)), 200)));
    final api = Api(
      MockClient(
        (_) async => http.Response(
          jsonEncode({
            'detail': {'code': 'no_heart'},
          }),
          402,
        ),
      ),
    );
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await settle(t);
    expect(find.text('Out of sunbeams. One refills every 10 minutes (next in 5 min).'), findsOneWidget);
  });

  testWidgets('접속만으로 오늘 출석되면(서버 attended_now) 잔고 막대가 알린다', (t) async {
    Auth.client = AuthClient(
      MockClient(
        (_) async => http.Response(jsonEncode({...wallet(coins: 200, claimed: true), 'attended_now': true}), 200),
      ),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await settle(t);
    expect(find.text('Checked in · 1 days in a row'), findsOneWidget);
  });

  testWidgets('홈 위에 미션 화면이 열려 있어도 출석 알림은 한 번만(맨 위 막대만)', (t) async {
    Auth.client = AuthClient(
      MockClient((_) async => http.Response(jsonEncode(wallet(coins: 200, claimed: true)), 200)),
    );
    final nav = GlobalKey<NavigatorState>();
    await t.pumpWidget(
      MaterialApp(
        navigatorKey: nav,
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: const Scaffold(body: WalletBar()),
      ),
    );
    await settle(t);
    nav.currentState!.push(MaterialPageRoute(builder: (_) => const Scaffold(body: WalletBar())));
    await settle(t);
    Wallet.attendedNow.value++;
    await t.pump();
    expect(find.text('Checked in · 1 days in a row'), findsOneWidget);
    for (var i = 0; i < 4; i++) {
      await t.pump(const Duration(seconds: 3)); // 첫 알림이 사라진 뒤(표시 4초 + 애니메이션)
    }
    expect(find.text('Checked in · 1 days in a row'), findsNothing); // 줄 선 두 번째 알림이 없다
    // 대화창이 맨 위에 있을 때 온 출석도 알린다(리뷰 10차)
    showDialog(
      context: nav.currentContext!,
      builder: (_) => const AlertDialog(content: Text('pick')),
    );
    await t.pump();
    await t.pump(const Duration(milliseconds: 500));
    Wallet.attendedNow.value++;
    await t.pump();
    await t.pump(const Duration(milliseconds: 500));
    expect(find.text('Checked in · 1 days in a row'), findsOneWidget);
  });

  test('출석한 조회 응답이 더 새 스냅숏보다 늦게 와 버려져도 출석 알림은 낸다', () async {
    final real = DateTime.now().millisecondsSinceEpoch / 1000;
    Wallet.set(wallet(v: real + 10, coins: 200, claimed: true), owner: Auth.me.value?.id); // 뒤 조회가 먼저 반영됨
    Auth.client = AuthClient(
      MockClient(
        (_) async =>
            http.Response(jsonEncode({...wallet(v: real, coins: 200, claimed: true), 'attended_now': true}), 200),
      ),
    );
    final before = Wallet.attendedNow.value;
    await Wallet.refresh();
    expect(Wallet.attendedNow.value, before + 1);
  });

  test('웹은 조회로 출석하지 않으니, 오늘 출석 전이면 출석 요청(POST)을 보내 접속만으로 출석한다', () async {
    final sent = <String>[];
    var claimed = false; // 서버의 오늘 출석 여부
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add('${r.method} ${r.url.path}');
        if (r.method == 'POST') claimed = true;
        return http.Response(jsonEncode(wallet(coins: 200, claimed: claimed)), 200);
      }),
    );
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Wallet.web = true;
    addTearDown(() => Wallet.web = false);
    final before = Wallet.attendedNow.value;
    await Wallet.refresh();
    expect(sent, ['GET /api/wallet', 'POST /api/wallet/attend']);
    expect(Wallet.attendedNow.value, before + 1);
    sent.clear();
    await Wallet.refresh(); // 이미 출석함 — 다시 보내지 않는다
    expect(sent, ['GET /api/wallet']);
  });

  test('웹 자동 출석: 다른 탭이 먼저 출석했으면(409) 잔고를 다시 읽고, 연결 실패면 실패로 돌려 다시 시도하게 한다', () async {
    final sent = <String>[];
    var claimed = false, down = false;
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add('${r.method} ${r.url.path}');
        if (r.method == 'POST') {
          if (down) return http.Response('', 503);
          claimed = true; // 다른 탭이 이미 출석
          return http.Response(
            jsonEncode({
              'detail': {'code': 'attended'},
            }),
            409,
          );
        }
        return http.Response(jsonEncode(wallet(coins: 200, claimed: claimed)), 200);
      }),
    );
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Wallet.web = true;
    addTearDown(() => Wallet.web = false);
    expect(await Wallet.refresh(), isNull);
    expect(sent, ['GET /api/wallet', 'POST /api/wallet/attend', 'GET /api/wallet']);
    expect(Wallet.current.value!.attended, isTrue);
    claimed = false;
    down = true;
    expect((await Wallet.refresh())!.$1, 503);
  });

  test('광고 보상 결과를 모르면 같은 계정은 같은 id로 다시 보내고, 다른 계정의 성공이 그 id를 지우지 않는다', () async {
    final rids = <String>[];
    var fail = true;
    Auth.client = AuthClient(
      MockClient((r) async {
        rids.add('${Auth.me.value!.id}:${(jsonDecode(r.body) as Map)['rid']}');
        return fail ? http.Response('', 503) : http.Response(jsonEncode(wallet(coins: 200)), 200);
      }),
    );
    Wallet.adRids.clear();
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    expect((await Wallet.watchAd(account: 1))!.$1, 503);
    expect(Wallet.adPending(1), isTrue);
    fail = false;
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'});
    expect(await Wallet.watchAd(account: 2), isNull);
    expect(Wallet.adPending(1), isTrue); // B의 성공이 A의 id를 지우지 않는다
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    expect(await Wallet.watchAd(account: 1), isNull);
    expect(rids[2], rids[0]); // A는 같은 id로 다시
    expect(Wallet.adPending(1), isFalse);
  });

  testWidgets('결과를 모르는 광고 보상은 앱을 다시 켜도 상점에서 확인만 한다', (t) async {
    final rids = <String>[];
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/ad') {
          rids.add(jsonDecode(r.body)['rid']);
          if (rids.length == 1) return http.Response('', 503); // 응답 유실
        }
        return http.Response(
          jsonEncode({
            ...wallet(),
            'ads': {'on': true, 'left': 5, 'hearts': 1, 'per_day': 5},
          }),
          200,
        );
      }),
    );
    await Wallet.watchAd(account: 1);
    Wallet.adRids.clear(); // 앱을 다시 켬(메모리는 비고 기기 저장만 남음, Codex 25차)
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await settle(t);
    expect(find.text('Check reward'), findsOneWidget);
    await t.tap(find.byKey(const ValueKey('ad-watch')));
    await settle(t);
    expect(find.byKey(const ValueKey('ad-playing')), findsNothing); // 다시 보지 않고
    expect(rids, [rids[0], rids[0]]); // 같은 id로 확인
    expect(Wallet.adPending(1), isFalse);
    expect(await Wallet.loadAdPending(1), isFalse); // 확정되면 기기에서도 지운다
    // 다른 탭이 남긴 미확정 보상이 둘이면 하나를 확인한 뒤 바로 다음 것을 '보상 확인'으로(Codex 28차)
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('adRid.1.x1', true);
    await prefs.setBool('adRid.1.x2', true);
    await t.pumpWidget(const SizedBox());
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('ad-watch')));
    await settle(t);
    expect(find.text('Check reward'), findsOneWidget);
    await t.tap(find.byKey(const ValueKey('ad-watch')));
    await settle(t);
    expect(find.text('Check reward'), findsNothing);
    expect(rids.sublist(2).toSet(), {'x1', 'x2'});
  });

  testWidgets('애니메이션 줄이기를 켜도 광고는 실제 5초가 지나야 보상을 요청한다', (t) async {
    t.platformDispatcher.accessibilityFeaturesTestValue = const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(t.platformDispatcher.clearAccessibilityFeaturesTestValue);
    final sent = <String>[];
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final ads = {
      ...wallet(),
      'ads': {'on': true, 'left': 5, 'hearts': 1, 'per_day': 5},
    };
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add(r.url.path);
        return http.Response(jsonEncode(ads), 200);
      }),
    );
    Wallet.set(ads, owner: 1);
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('ad-watch')));
    await t.pump(const Duration(seconds: 1));
    await t.pump(const Duration(seconds: 1));
    expect(sent, isNot(contains('/api/wallet/ad'))); // 막대가 빨리 끝나도(Codex 37차)
    // 화면을 떠나 있던 시간은 세지 않는다(Codex 38차)
    t.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await t.pump(const Duration(seconds: 10));
    expect(sent, isNot(contains('/api/wallet/ad')));
    // 막대도 같은 시청 시간 — 다 찬 채로 기다리게 하지 않는다(Codex 39차)
    expect(t.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator)).value, lessThan(.5));
    t.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await t.pump(const Duration(seconds: 4));
    await settle(t);
    expect(sent, contains('/api/wallet/ad'));
    Wallet.adRids.clear();
  });

  testWidgets('상점을 연 직후 남은 보상을 불러오기 전에는 광고 버튼을 누를 수 없다', (t) async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final ads = {
      ...wallet(),
      'ads': {'on': true, 'left': 5, 'hearts': 1, 'per_day': 5},
    };
    Auth.client = AuthClient(MockClient((r) async => http.Response(jsonEncode(ads), 200)));
    Wallet.set(ads, owner: 1);
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    // 첫 화면 — 기기 저장소를 아직 다 읽지 않았다(Codex 29차)
    expect(t.widget<FilledButton>(find.byKey(const ValueKey('ad-watch'))).onPressed, isNull);
    await settle(t);
    expect(t.widget<FilledButton>(find.byKey(const ValueKey('ad-watch'))).onPressed, isNotNull);
  });

  test('광고 보상은 누른 때 정한 id로 보낸다 — 그사이 다른 화면이 복구한 id로 바뀌지 않는다', () async {
    final sent = <String>[];
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add(jsonDecode(r.body)['rid']);
        return http.Response(jsonEncode(wallet()), 200);
      }),
    );
    Wallet.adRids[1] = 'restored'; // 닫힌 화면이 뒤늦게 복구한 id(Codex 30차)
    expect(await Wallet.watchAd(account: 1, rid: 'mine'), isNull);
    expect(sent, ['mine']);
    expect(Wallet.adRids[1], 'restored'); // 남의 id는 그대로 — 다음에 확인
    Wallet.adRids.clear();
  });

  test('같은 계정의 다른 탭이 적은 광고 id는 이 탭의 보상이 끝나도 남는다', () async {
    SharedPreferences.setMockInitialValues({'adRid.1.tab-b': true}); // B 탭이 보낸 뒤 결과를 모름
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(MockClient((r) async => http.Response(jsonEncode(wallet()), 200)));
    expect(await Wallet.watchAd(account: 1), isNull); // A 탭은 받음
    Wallet.adRids.clear(); // B 탭을 새로고침
    expect(await Wallet.loadAdPending(1), isTrue); // B의 id는 남아 확인만 한다(Codex 26차)
    expect(Wallet.adRids[1], 'tab-b');
    Wallet.adRids.clear();
    SharedPreferences.setMockInitialValues({}); // 다음 테스트에 남기지 않는다
  });

  testWidgets('상점 햇살 탭: 광고가 꺼져 있으면 준비 중, 켜지면 광고 자리를 본 뒤 햇살을 받는다', (t) async {
    var on = false, off = false, left = 5;
    final sent = <String>[];
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add('${r.method} ${r.url.path}');
        if (off) {
          on = false;
          if (r.url.path == '/api/wallet/ad') {
            return http.Response(
              jsonEncode({
                'detail': {'code': 'ads_off'},
              }),
              404,
            );
          }
        }
        if (r.url.path == '/api/wallet/ad') left--;
        return http.Response(
          jsonEncode({
            ...wallet(),
            'ads': {'on': on, 'left': left, 'hearts': 1, 'per_day': 5},
          }),
          200,
        );
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await settle(t);
    expect(find.text('Ad rewards are coming soon.'), findsOneWidget);
    expect(t.widget<FilledButton>(find.byKey(const ValueKey('ad-watch'))).onPressed, isNull);
    on = true;
    await Wallet.refresh();
    await t.pump();
    expect(find.text('5/5 left today'), findsOneWidget);
    await t.tap(find.byKey(const ValueKey('ad-watch')));
    await t.pump();
    expect(find.byKey(const ValueKey('ad-playing')), findsOneWidget); // 광고 자리부터
    expect(sent, isNot(contains('POST /api/wallet/ad')));
    await t.pump(const Duration(seconds: 6));
    await settle(t);
    expect(sent, contains('POST /api/wallet/ad'));
    expect(find.text('4/5 left today'), findsOneWidget);
    // 열어 둔 사이 서버에서 꺼지면: 보상은 ads_off로 거절되고 카드는 '준비 중'으로 바뀐다(Codex 24차)
    off = true;
    await t.tap(find.byKey(const ValueKey('ad-watch')));
    await t.pump();
    await t.pump(const Duration(seconds: 6));
    await settle(t);
    expect(find.text('Ad rewards are coming soon.'), findsOneWidget);
    expect(Wallet.adPending(1), isTrue); // 지급 여부를 모르니 같은 id를 남긴다
  });

  testWidgets('판이 끝난 응답의 지갑으로 잔고를 바로 바꾼다', (t) async {
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(coins: 1)), 200)));
    final done = {
      ...view(),
      'winner': 0,
      'settlement': [3, -1, -1, -1],
      'wallet': wallet(coins: 4321),
    };
    await t.pumpWidget(
      _wrap(
        TableScreen(
          api: Api(MockClient((_) async => http.Response(jsonEncode(done), 200))),
          showHelpOnFirstVisit: false,
        ),
      ),
    );
    await settle(t);
    expect(Wallet.current.value?.coins, 4321); // 응답에 지갑이 있으면 다시 받지 않는다(옛 값으로 덮지 않게)
  });

  test('계정이 바뀌거나 로그아웃하면 앞 사람 지갑을 비운다', () {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Wallet.set(wallet(coins: 999), owner: 1);
    expect(Wallet.current.value?.coins, 999);
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'});
    expect(Wallet.current.value, isNull);
    Wallet.set(wallet(coins: 5), owner: 1); // A 때 보낸 요청의 늦은 응답은 버린다
    expect(Wallet.current.value, isNull);
    Wallet.set(wallet(coins: 7), owner: 2);
    Auth.me.value = null;
    expect(Wallet.current.value, isNull);
  });

  test('새 판이 세 번 다 결과를 모르면 다음 새 판도 같은 요청 id로 보낸다', () async {
    final rids = <String>[];
    final api = Api(
      MockClient((r) async {
        rids.add(jsonDecode(r.body)['rid']);
        return rids.length <= 3 ? http.Response('', 502) : http.Response(jsonEncode(view()), 200);
      }),
    );
    await expectLater(api.newGame(), throwsA(isA<ApiError>()));
    final again = Api(api.client);
    await again.newGame(); // 화면을 새로 열어도
    expect(rids.toSet().length, 1);
    again.settle(); // 판 화면이 판을 다 보이면
    expect(Api.pendingNewGame, isEmpty); // 다음 판은 새 id
  });

  testWidgets('상점을 닫았다 열어도 결과를 모르는 구매는 같은 요청 id로 다시 보낸다', (t) async {
    final rids = <String>[];
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/buy') {
          rids.add(jsonDecode(r.body)['rid']);
          if (rids.length == 1) return http.Response('', 503);
        }
        return http.Response(jsonEncode(wallet(gems: 30)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'coins')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('buy-coins1000')));
    await t.pumpAndSettle();
    await t.pumpWidget(const SizedBox()); // 상점을 닫음
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'coins')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('buy-coins1000')));
    await t.pumpAndSettle();
    expect(rids, hasLength(2));
    expect(rids[0], rids[1]);
  });

  testWidgets('다음 하트가 차는 시각이 되면 잔고 막대가 다시 받아 온다', (t) async {
    var calls = 0;
    final next = DateTime.now().millisecondsSinceEpoch / 1000 + 3;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode(calls == 1 ? wallet(hearts: 0, next: next) : wallet(hearts: 1)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.hearts, 0);
    await t.pump(const Duration(seconds: 5));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.hearts, 1);
  });

  testWidgets('끝난 판 응답이 유실돼 다시 받으면 그 응답의 지갑으로 바꾼다', (t) async {
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(coins: 1)), 200)));
    final done = {
      ...view(),
      'winner': 0,
      'settlement': [3, -1, -1, -1],
      'wallet': wallet(coins: 777, v: 4e9),
    }; // 서버가 나중에 찍은 지갑
    final api = Api(
      MockClient((r) async {
        if (r.url.path.endsWith('/moves')) return http.Response('', 502);
        if (r.method == 'GET') return http.Response(jsonEncode(done), 200);
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await settle(t);
    expect(Wallet.current.value?.coins, 777);
  });

  testWidgets('늦게 온 옛 조회 응답(서버 시각이 옛것)이 출석 뒤 잔고를 덮지 않는다', (t) async {
    final slow = Completer<http.Response>();
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/attend') {
          return http.Response(jsonEncode(wallet(coins: 200, claimed: true)), 200);
        }
        if (++gets == 2) return slow.future; // 두 번째 조회가 늦게 온다
        return http.Response(jsonEncode(wallet()), 200);
      }),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    final late = Wallet.refresh();
    await t.tap(find.byKey(const ValueKey('attend')));
    await t.pumpAndSettle();
    slow.complete(http.Response(jsonEncode(wallet(v: 0.5)), 200)); // 서버가 출석 전에 처리한 조회(옛 시각)
    await late;
    await t.pumpAndSettle();
    expect(Wallet.current.value?.coins, 200);
    expect(Wallet.current.value?.attended, isTrue);
  });

  test('한국 자정 계산', () {
    final before = DateTime.utc(2026, 11, 25, 14, 59, 59).millisecondsSinceEpoch; // 23:59:59 KST
    expect(nextKstMidnight(before), DateTime.utc(2026, 11, 25, 15).millisecondsSinceEpoch);
    final after = DateTime.utc(2026, 11, 25, 15).millisecondsSinceEpoch; // 자정 정각이면 다음 날 자정
    expect(nextKstMidnight(after), DateTime.utc(2026, 11, 26, 15).millisecondsSinceEpoch);
  });

  testWidgets('하트가 가득해도 한국 자정이 지나면 다시 받아 온다(새날 출석·미션)', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode(wallet(claimed: calls == 1)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.attended, isTrue);
    await t.pump(const Duration(hours: 25));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.attended, isFalse);
  });

  testWidgets('결과를 모르는 구매는 보석이 줄어 보여도 다시 눌러 확인할 수 있다', (t) async {
    Wallet.buyRids[(null, 'hearts5')] = 'pendingrid1';
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(gems: 0)), 200)));
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await t.pumpAndSettle();
    expect(t.widget<FilledButton>(find.byKey(const ValueKey('buy-hearts5'))).onPressed, isNotNull);
    expect(t.widget<FilledButton>(find.byKey(const ValueKey('buy-hearts15'))).onPressed, isNull);
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pumpAndSettle();
    expect(Wallet.buyRids, isEmpty);
  });

  testWidgets('판 응답이 오기 전에 계정이 바뀌면 그 판의 지갑을 다음 사람에게 넣지 않는다', (t) async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(coins: 1)), 200)));
    final slow = Completer<http.Response>();
    final done = {
      ...view(),
      'winner': 0,
      'settlement': [3, -1, -1, -1],
      'wallet': wallet(coins: 9999),
    };
    final api = Api(
      MockClient((r) async => r.url.path.endsWith('/moves') ? slow.future : http.Response(jsonEncode(view()), 200)),
    );
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await t.pump();
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'}); // A 로그아웃 → B 로그인
    slow.complete(http.Response(jsonEncode(done), 200));
    await settle(t);
    expect(Wallet.current.value?.coins, isNot(9999));
  });

  test('새 판을 다시 보내기 전에 계정이 바뀌었으면 다시 보내지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    var calls = 0;
    final api = Api(
      MockClient((_) async {
        calls++;
        Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'});
        return http.Response('', 502);
      }),
    );
    await expectLater(api.newGame(), throwsA(isA<ApiError>()));
    expect(calls, 1);
  });

  testWidgets('출석 응답이 그 뒤에 보낸 조회보다 늦게 와도 출석 결과를 반영한다', (t) async {
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/attend') return slow.future;
        return http.Response(jsonEncode(wallet()), 200); // 서버가 출석보다 먼저 처리한 조회
      }),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('attend')));
    await t.pump();
    await Wallet.refresh();
    slow.complete(http.Response(jsonEncode(wallet(coins: 200, claimed: true)), 200));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.coins, 200);
  });

  testWidgets('예약한 하트 조회가 실패하면 30초 뒤 다시 받는다', (t) async {
    var calls = 0;
    final next = DateTime.now().millisecondsSinceEpoch / 1000 + 3;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        if (calls == 2) return http.Response('', 503);
        return http.Response(jsonEncode(calls == 1 ? wallet(hearts: 0, next: next) : wallet(hearts: 1)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    await t.pump(const Duration(seconds: 5));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.hearts, 0); // 한 번 실패
    await t.pump(const Duration(seconds: 31));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.hearts, 1);
  });

  testWidgets('구매 응답이 늦게 와도 그 뒤 서버가 처리한 조회(새 판으로 하트가 준 잔고)를 덮지 않는다', (t) async {
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/buy') return slow.future;
        return http.Response(jsonEncode(wallet(gems: 0, hearts: 14)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await t.pumpAndSettle();
    Wallet.set(wallet(gems: 10, hearts: 10), owner: null);
    await t.pump();
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pump();
    final bought = wallet(gems: 0, hearts: 15); // 서버가 먼저 처리한 구매
    await Wallet.refresh(); // 그 뒤 처리된 조회(새 판으로 하트 1 씀)
    slow.complete(http.Response(jsonEncode(bought), 200));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.hearts, 14);
  });

  test('앞 계정이 보낸 지갑 요청의 늦은 401은 지금 계정을 로그아웃시키지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(MockClient((_) => slow.future));
    final pending = Wallet.refresh();
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'});
    slow.complete(http.Response('{"detail":{"code":"session"}}', 401));
    await pending;
    expect(Auth.me.value?.id, 2);
  });

  testWidgets('첫 조회가 실패해도 30초 뒤 다시 받아 미션 화면이 빈 채 멈추지 않는다', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async => ++calls == 1 ? http.Response('', 503) : http.Response(jsonEncode(wallet()), 200)),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pump();
    await t.pump();
    expect(find.byKey(const ValueKey('attend')), findsNothing);
    await t.pump(const Duration(seconds: 31));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('attend')), findsOneWidget);
  });

  test('다른 탭에서 다른 계정으로 로그인했으면(409 account_changed) 지금 쿠키의 계정을 다시 읽는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final sent = <String?>[];
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add(r.headers['x-kumoniji-account']);
        if (r.url.path == '/api/auth/me') return http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200);
        return http.Response('{"detail":{"code":"account_changed"}}', 409);
      }),
    );
    await Wallet.refresh();
    await Future<void>.delayed(Duration.zero);
    expect(sent.first, '1'); // 이 화면의 계정을 보낸다
    expect(sent.last, isNull); // 다시 읽기에는 옛 계정을 안 붙인다
    expect(Auth.me.value?.id, 2);
    expect(Wallet.current.value, isNull);
  });

  test('요청 중 같은 세션의 내 정보 다시 읽기가 끼어도 409 account_changed면 계정을 다시 읽는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final slow = Completer<http.Response>();
    var meCalls = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/me') {
          return http.Response(
            jsonEncode(++meCalls == 1 ? {'id': 1, 'nickname': 'a'} : {'id': 2, 'nickname': 'b'}),
            200,
          );
        }
        return slow.future;
      }),
    );
    final refresh = Wallet.refresh();
    await Future<void>.delayed(Duration.zero);
    await Auth.reload(); // 같은 세션 — 새 Me 객체가 들어감
    slow.complete(http.Response('{"detail":{"code":"account_changed"}}', 409)); // 그사이 다른 탭이 B로
    await refresh;
    await Future<void>.delayed(Duration.zero);
    expect(Auth.me.value?.id, 2);
  });

  test('앞 구매의 늦은 성공 응답이 그 뒤 새로 받은 구매 id를 지우지 않는다', () async {
    final first = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(
      MockClient((r) async => ++n == 1 ? first.future : http.Response(jsonEncode(wallet(gems: 30)), 200)),
    );
    Wallet.buyRids[(null, 'hearts5')] = 'oldrid001';
    final late = Wallet.buy('hearts5', account: null);
    Wallet.buyRids[(null, 'hearts5')] = 'newrid002'; // 그사이 다음 구매가 새 id를 받음(결과 모름)
    first.complete(http.Response(jsonEncode(wallet(gems: 20)), 200));
    await late;
    expect(Wallet.buyRids[(null, 'hearts5')], 'newrid002');
  });

  test('같은 구매 id로 겹친 두 호출 — 앞이 성공하고 뒤 응답이 사라져도 같은 구매라 둘 다 성공(리뷰 42·43차)', () async {
    final first = Completer<http.Response>(), second = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(MockClient((r) async => ++n == 1 ? first.future : second.future));
    Wallet.buyRids.clear();
    final a = Wallet.buy('hearts5', account: null); // 상점을 닫았다 다시 열어 같은 상품을 또 누름
    final b = Wallet.buy('hearts5', account: null);
    await Future<void>.delayed(Duration.zero);
    final rid = Wallet.buyRids[(null, 'hearts5')];
    first.complete(http.Response(jsonEncode(wallet(gems: 20)), 200));
    await a;
    expect(Wallet.buyRids[(null, 'hearts5')], rid); // 두 번째가 아직 기다림
    second.complete(http.Response('', 503)); // 두 번째 응답 유실
    expect(await b, isNull); // 같은 id = 같은 구매, 서버가 처리했음 — 실패로 안내하지 않는다(그러면 다시 눌러 보석을 또 씀)
    expect(Wallet.buyRids, isEmpty); // 다음 구매는 새 id
  });

  test('같은 구매 id로 겹친 두 호출 — 나중 호출이 먼저 성공하고 앞 호출이 실패해도 마지막에 id를 지운다(리뷰 43차)', () async {
    final first = Completer<http.Response>(), second = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(MockClient((r) async => ++n == 1 ? first.future : second.future));
    Wallet.buyRids.clear();
    final a = Wallet.buy('hearts5', account: null);
    final b = Wallet.buy('hearts5', account: null);
    await Future<void>.delayed(Duration.zero);
    second.complete(http.Response(jsonEncode(wallet(gems: 20)), 200)); // 나중 호출이 먼저 성공
    await b;
    expect(Wallet.buyRids, isNotEmpty); // 앞 호출이 아직 기다림
    first.complete(http.Response('', 503)); // 앞 호출은 결과 모름
    expect(await a, isNull);
    expect(Wallet.buyRids, isEmpty); // 서버는 처리했음 — 다음 구매는 새 id(옛 id로 보내 새 구매가 묻히지 않게)
  });

  test('앞 새 판의 늦은 응답이 그 뒤 새로 받은 새 판 id를 지우지 않는다', () async {
    final api = Api(
      MockClient((r) async {
        Api.pendingNewGame[null] = 'newrid002'; // 요청이 나간 뒤 다른 화면이 새 id로 보냄(결과 모름)
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await api.newGame();
    expect(Api.pendingNewGame[null], 'newrid002');
  });

  test('결과를 모르는 새 판 뒤 세션이 끝나도(401) 요청 id를 남겨 다시 로그인한 뒤 같은 id로 보낸다', () async {
    final rids = <String>[];
    final api = Api(
      MockClient((r) async {
        if (r.url.path != '/api/games') return http.Response('{}', 404);
        rids.add(jsonDecode(r.body)['rid']);
        return switch (rids.length) {
          1 => http.Response('', 502),
          2 => http.Response('{"detail":{"code":"session"}}', 401),
          _ => http.Response(jsonEncode(view()), 200),
        };
      }),
    );
    await expectLater(api.newGame(), throwsA(isA<ApiError>()));
    await api.newGame();
    expect(rids.toSet().length, 1);
  });

  test('다시 보내는 요청(CSRF·세션 갱신 뒤 복사본)은 처음 붙인 계정 번호를 그대로 둔다', () async {
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'}); // 그사이 다른 요청이 B를 읽어 옴
    final sent = <String?>[];
    final client = AuthClient(
      MockClient((r) async {
        sent.add(r.headers['x-kumoniji-account']);
        return http.Response('{}', 200);
      }),
    );
    final again = http.Request('POST', Uri.parse('https://k/api/wallet/buy'))..headers['x-kumoniji-account'] = '1';
    await client.send(again); // A 때 시작한 요청의 복사본
    expect(sent, ['1']);
  });

  test('보관한 새 판 id로 다시 보낸 첫 시도가 401이어도 id를 지우지 않는다', () async {
    Api.pendingNewGame[null] = 'keptrid0001'; // 앞 호출이 결과를 모르고 끝남
    final api = Api(MockClient((_) async => http.Response('{"detail":{"code":"session"}}', 401)));
    await expectLater(api.newGame(), throwsA(isA<ApiError>()));
    expect(Api.pendingNewGame[null], 'keptrid0001');
  });

  test('세션이 끝나 로그아웃돼도 결과를 모르는 구매 id는 계정별로 남는다', () {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Wallet.buyRids[(1, 'hearts5')] = 'keptbuy001';
    Auth.me.value = null;
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    expect(Wallet.pendingBuy('hearts5'), isTrue);
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'});
    expect(Wallet.pendingBuy('hearts5'), isFalse); // 다른 계정에는 안 씀
  });

  test('세션 갱신 뒤 다시 보낸 요청이 409 account_changed여도 계정을 다시 읽는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    var n = 0;
    final client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/refresh') return http.Response('{"access":"a2","refresh":"r2"}', 200);
        if (r.url.path == '/api/auth/me') return http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200);
        return ++n == 1
            ? http.Response('{"detail":{"code":"session"}}', 401)
            : http.Response('{"detail":{"code":"account_changed"}}', 409);
      }),
    );
    Auth.client = client..keep({'access': 'a1', 'refresh': 'r1'});
    await client.send(http.Request('GET', Uri.parse('https://k/api/wallet')));
    await Future<void>.delayed(Duration.zero);
    expect(Auth.me.value?.id, 2);
  });

  test('앞 계정이 보낸 요청의 늦은 409 account_changed는 이미 바뀐 계정을 비우지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'});
    final client = AuthClient(MockClient((_) async => http.Response('{"detail":{"code":"account_changed"}}', 409)));
    final old = http.Request('GET', Uri.parse('https://k/api/wallet'))..headers['x-kumoniji-account'] = '1';
    await client.send(old);
    expect(Auth.me.value?.id, 2);
  });

  test('다음 하트까지 남은 시간은 서버 시각으로 잰다(기기 시계가 어긋나도)', () {
    final now = DateTime.now().millisecondsSinceEpoch / 1000;
    final w = WalletState(wallet(t: now + 120, next: now + 120 + 50)); // 서버가 2분 빠름, 서버 기준 50초 뒤 충전
    expect(minutesToHeart(w), 1);
  });

  test('판 화면은 연 계정에 묶인다 — 그 뒤 계정이 바뀌면 새 판을 보내지 않고, 보내는 요청엔 연 계정 번호', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final sent = <String?>[];
    final api = Api(
      MockClient((r) async {
        sent.add(r.headers['x-kumoniji-account']);
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await api.get('a');
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'}); // 화면이 닫히는 사이 계정이 바뀜
    await expectLater(api.newGame(), throwsA(isA<ApiError>()));
    expect(sent, ['1']);
  });

  testWidgets('판 화면은 열 때의 계정으로 묶인다(패 그림 준비를 기다리는 사이 바뀌어도)', (t) async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final sent = <String?>[];
    final screen = TableScreen(showHelpOnFirstVisit: false);
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add(r.headers['x-kumoniji-account']);
        return http.Response(jsonEncode(r.url.path == '/api/games' ? view() : wallet()), 200);
      }),
    );
    await t.pumpWidget(_wrap(screen));
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'}); // 첫 새 판을 보내기 전에 계정이 바뀜
    await settle(t);
    expect(sent.where((h) => h == '2'), isEmpty);
  });

  testWidgets('자정을 넘겨 기다린 요청의 전날 상태를 받으면 곧 다시 받는다', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode(calls == 1 ? wallet(day: '2000-01-01', claimed: true) : wallet()), 200);
      }),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    await t.pump(const Duration(seconds: 2));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.attended, isFalse);
  });

  testWidgets('자정을 넘긴 스냅숏이 연달아 와도 곧바로 다시 받기가 지워지지 않는다(리뷰 44차)', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode(calls == 1 ? wallet(day: '2000-01-01', claimed: true) : wallet()), 200);
      }),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pump(); // 첫 조회(전날 상태) → 곧바로 다시 받기를 잡음
    await t.pump(const Duration(milliseconds: 100));
    Wallet.set(wallet(day: '2000-01-01', claimed: true), owner: null); // 다른 화면의 조회도 자정을 넘겨 전날 상태
    await t.pump(const Duration(seconds: 2));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.attended, isFalse);
  });

  testWidgets('판 화면에서 새 판 뒤 지갑 받기가 실패하면 홈의 잔고 막대가 30초 뒤 다시 받는다', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        if (calls == 2) return http.Response('', 503);
        return http.Response(jsonEncode(wallet(hearts: calls == 1 ? 10 : 9)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    await Wallet.refreshOrRetry(); // 판 화면이 부른 것 — 503
    await t.pump(const Duration(seconds: 31));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.hearts, 9);
  });

  test('다른 탭이 계정을 바꾼 뒤 내 정보 읽기가 연결 오류로 실패하면 다시 시도해 바뀐 계정을 읽는다', () async {
    var tries = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (++tries == 1) throw http.ClientException('offline');
        if (tries == 2) return http.Response('', 503); // 서버가 잠깐 503
        return http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200);
      }),
    );
    await Auth.reloadAfterSwitch();
    expect(Auth.me.value?.id, 2);
    expect(tries, 3);
  });

  test('계정을 다시 읽는 사이 직접 로그인하면 늦은 응답으로 덮지 않는다', () async {
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(MockClient((_) => slow.future));
    final pending = Auth.reloadAfterSwitch();
    Auth.me.value = Me.fromJson({'id': 3, 'nickname': 'c'}); // 그사이 C로 로그인
    slow.complete(http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200));
    await pending;
    expect(Auth.me.value?.id, 3);
  });

  test('계정을 다시 읽는 사이 직접 로그인을 시작하면 옛 계정 응답이 먼저 와도 새 로그인 결과가 들어간다', () async {
    final oldMe = Completer<http.Response>(), newMe = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(MockClient((_) => ++n == 1 ? oldMe.future : newMe.future));
    final pending = Auth.reloadAfterSwitch();
    final login = Auth.load(); // 그사이 B로 로그인 — 아직 응답 전
    oldMe.complete(http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200));
    await pending;
    newMe.complete(http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200));
    await login;
    expect(Auth.me.value?.id, 2);
  });

  test('A로 보이는 동안 내 정보 다시 읽기 사이 B 로그인을 시작하면 A의 늦은 응답이 B 결과를 밀어내지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final oldMe = Completer<http.Response>(), newMe = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(MockClient((_) => ++n == 1 ? oldMe.future : newMe.future));
    final reading = Auth.reload();
    final login = Auth.load(); // 그사이 B로 로그인 — 아직 응답 전
    oldMe.complete(http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200));
    await reading;
    newMe.complete(http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200));
    await login;
    expect(Auth.me.value?.id, 2);
  });

  test('로그인을 연달아 하면 앞 로그인의 내 정보 응답이 먼저 와도 나중 로그인 결과가 들어간다', () async {
    final aMe = Completer<http.Response>(), bMe = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(MockClient((_) => ++n == 1 ? aMe.future : bMe.future));
    final a = Auth.load();
    final b = Auth.load();
    aMe.complete(http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200));
    await a;
    bMe.complete(http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200));
    await b;
    expect(Auth.me.value?.id, 2);
  });

  testWidgets('새 판 결과를 모른 채 끝나면(재시도도 실패) 잔고를 다시 받는다', (t) async {
    var walletCalls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        walletCalls++;
        return http.Response(jsonEncode(wallet(hearts: 9)), 200);
      }),
    );
    final api = Api(MockClient((_) async => http.Response('', 502)));
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await settle(t);
    await t.pump(const Duration(seconds: 3));
    await settle(t);
    expect(walletCalls, greaterThan(0));
    expect(Wallet.current.value?.hearts, 9);
  });

  testWidgets('계정이 비워진 뒤 남은 상점에서 누른 구매는 보내지 않는다', (t) async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    var bought = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/buy') bought++;
        return http.Response(jsonEncode(wallet(gems: 30)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await t.pumpAndSettle();
    Auth.me.value = null; // 다른 탭이 계정을 바꿈 — 화면은 다음 프레임까지 남아 있다
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pumpAndSettle();
    expect(bought, 0);
  });

  test('같은 id로 다른 화면이 아직 기다리는 중이면 이 호출의 402로 id를 지우지 않는다', () async {
    final slow = Completer<http.Response>();
    var n = 0;
    final client = MockClient(
      (_) => ++n == 1 ? slow.future : Future.value(http.Response('{"detail":{"code":"no_heart"}}', 402)),
    );
    Api.pendingNewGame[null] = 'sharedrid1';
    final a = Api(client).newGame().then<void>((_) {}, onError: (_) {});
    await expectLater(Api(client).newGame(), throwsA(isA<ApiError>()));
    expect(Api.pendingNewGame[null], 'sharedrid1');
    slow.complete(http.Response(jsonEncode(view()), 200));
    await a;
  });

  test('지갑 응답이 멈추면 시간 제한 뒤 실패로 돌려준다', () async {
    Auth.client = AuthClient(MockClient((_) => Completer<http.Response>().future))
      ..timeout = const Duration(milliseconds: 50);
    expect((await Wallet.refresh())?.$1, 0);
  });

  testWidgets('판이 끝났는데 지갑이 없으면(서버가 기록을 다시 시도 중) 잠시 뒤 잔고를 다시 받는다', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode(wallet(coins: 300)), 200);
      }),
    );
    final done = {
      ...view(),
      'winner': 0,
      'settlement': [3, -1, -1, -1],
    };
    await t.pumpWidget(
      _wrap(
        Stack(
          children: [
            TableScreen(
              api: Api(MockClient((_) async => http.Response(jsonEncode(done), 200))),
              showHelpOnFirstVisit: false,
            ),
            const Material(child: WalletBar()), // 홈 화면의 잔고 막대(판 화면 밑에 남아 있다)
          ],
        ),
      ),
    );
    await settle(t);
    await t.pump(const Duration(seconds: 140));
    await settle(t);
    expect(calls, 5); // 막대의 첫 조회 + 4·14·75·135초(서버 시도 2·12·72·132초 뒤)
    expect(Wallet.current.value?.coins, 300);
  });

  test('새 판 응답이 멈추면 시간 제한 뒤 같은 id로 다시 보낸다', () async {
    final rids = <String>[];
    final api = Api(
      AuthClient(
        MockClient((r) {
          rids.add(jsonDecode(r.body)['rid']);
          return rids.length == 1
              ? Completer<http.Response>().future
              : Future.value(http.Response(jsonEncode(view()), 200));
        }),
      )..timeout = const Duration(milliseconds: 50),
    );
    await api.newGame();
    expect(rids.length, 2);
    expect(rids.toSet().length, 1);
  });

  testWidgets('마지막 수 응답이 유실돼 다시 받은 끝난 판에 지갑이 없어도 잠시 뒤 잔고를 다시 받는다', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode(wallet(coins: 300)), 200);
      }),
    );
    final done = {
      ...view(),
      'winner': 0,
      'settlement': [3, -1, -1, -1],
    };
    var sent = 0;
    final api = Api(
      MockClient((r) async {
        if (r.method == 'POST' && r.url.path == '/api/games') return http.Response(jsonEncode(view()), 200);
        if (r.url.path.endsWith('/moves')) {
          sent++;
          return http.Response('', 502); // 마지막 수 — 서버는 처리했지만 응답 유실
        }
        return http.Response(jsonEncode(done), 200); // 다시 받기 — 끝난 판, 지갑 없음
      }),
    );
    await t.pumpWidget(
      _wrap(
        Stack(
          children: [
            TableScreen(api: api, showHelpOnFirstVisit: false),
            const Material(child: WalletBar()),
          ],
        ),
      ),
    );
    await settle(t);
    final before = calls;
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await t.pump(const Duration(seconds: 140));
    await settle(t);
    expect(sent, greaterThan(0));
    expect(calls - before, greaterThanOrEqualTo(4));
  });

  test('같은 계정으로 다시 로그인한 뒤 옛 세션 지갑 요청의 늦은 401은 새 로그인을 끊지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(
      MockClient((r) => r.url.path == '/api/auth/refresh' ? Future.value(http.Response('', 401)) : slow.future),
    );
    final pending = Wallet.refresh();
    Auth.me.value = null; // 로그아웃
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'}); // 같은 계정으로 다시 로그인
    slow.complete(http.Response('', 401));
    await pending;
    expect(Auth.me.value?.id, 1);
  });

  test('계정 바뀜 뒤 다시 읽기가 응답 없이 멈추면 시간 제한 뒤 다시 시도한다', () async {
    var tries = 0;
    Auth.client = AuthClient(
      MockClient((_) {
        if (++tries == 1) return Completer<http.Response>().future;
        return Future.value(http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200));
      }),
    )..timeout = const Duration(milliseconds: 50);
    await Auth.reloadAfterSwitch();
    expect(Auth.me.value?.id, 2);
  });

  test('같은 계정으로 다시 로그인한 뒤 옛 세션 요청의 늦은 409 account_changed는 새 로그인을 비우지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(
      MockClient((r) => r.url.path == '/api/wallet' ? slow.future : Future.value(http.Response('', 404))),
    );
    final pending = Wallet.refresh();
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'}); // 그사이 같은 계정으로 다시 로그인(새 세션)
    final fresh = Auth.me.value;
    slow.complete(http.Response('{"detail":{"code":"account_changed"}}', 409));
    await pending;
    expect(identical(Auth.me.value, fresh), isTrue);
  });

  test('같은 계정으로 다시 로그인하고 내 정보를 다시 읽은 뒤에도 옛 세션 요청의 늦은 409는 새 로그인을 비우지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(
      MockClient(
        (r) => r.url.path == '/api/wallet'
            ? slow.future
            : Future.value(http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200)),
      ),
    );
    await Auth.reload(); // 옛 세션의 다시 읽기 객체
    final pending = Wallet.refresh();
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'}); // 같은 계정으로 다시 로그인(새 세션)
    await Auth.reload(); // 새 세션의 다시 읽기 객체
    final fresh = Auth.me.value;
    slow.complete(http.Response('{"detail":{"code":"account_changed"}}', 409));
    await pending;
    await Future<void>.delayed(Duration.zero);
    expect(identical(Auth.me.value, fresh), isTrue);
  });

  test('머리글 뒤 본문이 멈춰도 시간 제한으로 끝난다', () async {
    final c = AuthClient(
      MockClient.streaming((r, _) async => http.StreamedResponse(StreamController<List<int>>().stream, 200)),
    )..timeout = const Duration(milliseconds: 50);
    await expectLater(c.get(Uri.parse('https://k/api/wallet')), throwsA(isA<TimeoutException>()));
  });

  testWidgets('서버 시계가 뒤로 보정돼 날이 계속 어긋나도 1초마다 다시 받지 않는다', (t) async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode(wallet(day: '2000-01-01')), 200);
      }),
    );
    await t.pumpWidget(_wrap(const Scaffold(body: WalletBar())));
    await t.pumpAndSettle();
    await t.pump(const Duration(seconds: 10));
    await t.pumpAndSettle();
    expect(calls, lessThanOrEqualTo(2));
  });

  test('동시에 나가 있던 두 조회는 v로 순서를 정한다 — 먼저 처리된(작은 v) 응답이 늦게 와도 버린다', () async {
    final first = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(
      MockClient(
        (_) => ++n == 1 ? first.future : Future.value(http.Response(jsonEncode(wallet(coins: 9, v: 2e9)), 200)),
      ),
    );
    final a = Wallet.refresh(); // 먼저 보냄
    await Wallet.refresh(); // 나중에 보낸 것이 먼저 옴(v 큼)
    first.complete(http.Response(jsonEncode(wallet(coins: 1, v: 1e9)), 200));
    await a;
    expect(Wallet.current.value?.coins, 9);
  });

  test('충전까지 남은 시간은 순서 번호(v)가 아니라 서버 실제 시각(t)으로 잰다', () {
    final now = DateTime.now().millisecondsSinceEpoch / 1000;
    // v는 순서 번호(시각이 아님) — 실제 시각 t는 지금, 충전은 10분 뒤
    Wallet.set(wallet(v: now + 1800, t: now, hearts: 9, next: now + 600), owner: null);
    expect(minutesToHeart(Wallet.current.value), 10);
  });

  test('403 mfa 뒤 내 정보를 다시 읽는 사이 다른 계정으로 로그인하면 늦은 응답으로 덮지 않는다', () async {
    final a = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.me.value = a;
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(MockClient((_) => slow.future));
    final pending = Auth.reloadIfStill(a);
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'});
    slow.complete(http.Response(jsonEncode({'id': 1, 'nickname': 'a', 'mfa_enabled': true, 'mfa_passed': false}), 200));
    await pending;
    expect(Auth.me.value?.id, 2);
  });

  testWidgets('지금 출석하면 7일째인 날은 버튼에 실제 보상(판돈 500·보석 10)을 보인다', (t) async {
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode(wallet(next7: true)), 200)));
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    expect(find.text('Check in today (+500 · 10 rainbow shards)'), findsOneWidget);
  });

  testWidgets('출석이 409(이미 받음)인데 잔고 받기도 실패하면 30초 뒤 다시 받아 버튼을 끈다', (t) async {
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/attend') return http.Response('{"detail":{"code":"attended"}}', 409);
        gets++;
        if (gets == 2) return http.Response('', 503);
        return http.Response(jsonEncode(wallet(claimed: gets > 2)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('attend')));
    await t.pumpAndSettle();
    await t.pump(const Duration(seconds: 31));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.attended, isTrue);
  });

  test('403 mfa 뒤 내 정보 읽기가 연결 오류면 세션이 그대로인 동안 다시 시도한다', () async {
    final a = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.me.value = a;
    var tries = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        if (++tries == 1) throw http.ClientException('offline');
        return http.Response(jsonEncode({'id': 1, 'nickname': 'a', 'mfa_enabled': true, 'mfa_passed': false}), 200);
      }),
    );
    await Auth.reloadIfStill(a);
    expect(Auth.me.value?.needsMfa, isTrue);
  });

  test('시간 제한이 지나면 요청 자체를 끊는다(늦은 응답의 쿠키가 다른 계정을 덮지 않게)', () async {
    http.BaseRequest? seen;
    final c = AuthClient(
      MockClient.streaming((r, _) {
        seen = r;
        return Completer<http.StreamedResponse>().future;
      }),
    )..timeout = const Duration(milliseconds: 50);
    await expectLater(c.post(Uri.parse('https://k/api/wallet/buy')), throwsA(isA<TimeoutException>()));
    final trigger = (seen! as http.Abortable).abortTrigger;
    var aborted = false;
    await trigger!.then((_) => aborted = true).timeout(const Duration(seconds: 1));
    expect(aborted, isTrue);
  });

  testWidgets('첫 판을 기다리다 화면을 닫으면 그 판의 요청 id를 남겨 다음에 같은 판을 받는다', (t) async {
    final slow = Completer<http.Response>();
    final rids = <String>[];
    final api = Api(
      MockClient((r) {
        rids.add(jsonDecode(r.body)['rid']);
        return rids.length == 1 ? slow.future : Future.value(http.Response(jsonEncode(view()), 200));
      }),
    );
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await t.pump();
    await t.pumpWidget(_wrap(const SizedBox())); // 응답 전에 홈으로
    slow.complete(http.Response(jsonEncode(view()), 200)); // 서버는 하트를 쓰고 판을 만들었다
    await t.pump();
    await Api(
      MockClient((r) async {
        rids.add(jsonDecode(r.body)['rid']);
        return http.Response(jsonEncode(view()), 200);
      }),
    ).newGame();
    expect(rids.length, 2);
    expect(rids.toSet().length, 1);
  });

  testWidgets('보석 부족 거절 뒤 잔고 받기도 실패하면 30초 뒤 다시 받는다', (t) async {
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/buy') return http.Response('{"detail":{"code":"gems"}}', 409);
        gets++;
        if (gets == 2) return http.Response('', 503);
        return http.Response(jsonEncode(wallet(gems: gets > 2 ? 3 : 30)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pumpAndSettle();
    await t.pump(const Duration(seconds: 31));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.gems, 3);
  });

  testWidgets('새 판 재시도를 기다리는 사이 화면을 닫으면 더 보내지 않는다(id는 남김)', (t) async {
    var sent = 0;
    final api = Api(
      MockClient((_) async {
        sent++;
        return http.Response('', 502);
      }),
    );
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await t.pump(const Duration(milliseconds: 100)); // 첫 요청 실패 → 재시도 대기
    await t.pumpWidget(_wrap(const SizedBox())); // 홈으로
    await t.pump(const Duration(seconds: 3));
    expect(sent, 1);
    expect(Api.pendingNewGame, isNotEmpty);
  });

  test('2단계 인증 상태를 다시 읽다 401이면 갱신해 다시 읽는다', () async {
    final a = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.me.value = a;
    var mes = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/refresh') return http.Response(jsonEncode({'access': 'A2', 'refresh': 'r2'}), 200);
        if (++mes == 1) return http.Response('{"detail":{"code":"session"}}', 401);
        return http.Response(jsonEncode({'id': 1, 'nickname': 'a', 'mfa_enabled': true, 'mfa_passed': false}), 200);
      }),
    )..keep({'access': 'A', 'refresh': 'r'});
    await Auth.reloadIfStill(a);
    expect(Auth.me.value?.needsMfa, isTrue);
  });

  testWidgets('구매 결과를 모르면(503) 잔고를 다시 받는다', (t) async {
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/buy') return http.Response('', 503); // 서버는 처리했지만 응답 유실
        gets++;
        return http.Response(jsonEncode(wallet(gems: gets > 1 ? 20 : 30)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.gems, 20);
  });

  test('보내기 전에 화면이 닫혔으면 첫 새 판 요청도 보내지 않는다', () async {
    var sent = 0;
    final api = Api(
      MockClient((_) async {
        sent++;
        return http.Response(jsonEncode(view()), 200);
      }),
    )..wanted = (() => false);
    await expectLater(api.newGame(), throwsA(isA<ApiError>()));
    expect(sent, 0);
  });

  testWidgets('구매 결과를 모르는 채 상점을 닫았어도 잔고를 다시 받는다', (t) async {
    final slow = Completer<http.Response>();
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((r) {
        if (r.url.path == '/api/wallet/buy') return slow.future;
        gets++;
        return Future.value(http.Response(jsonEncode(wallet(gems: gets > 1 ? 20 : 30)), 200));
      }),
    );
    await t.pumpWidget(_wrap(const ShopScreen(tab: 'hearts')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('buy-hearts5')));
    await t.pump();
    await t.pumpWidget(_wrap(const SizedBox())); // 상점을 닫음
    slow.complete(http.Response('', 503)); // 서버는 처리했지만 응답 유실
    await t.pumpAndSettle();
    expect(Wallet.current.value?.gems, 20);
  });

  testWidgets('새 판 결과를 모르는 채 판 화면을 닫았어도 잔고를 다시 받는다', (t) async {
    final slow = Completer<http.Response>();
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        gets++;
        return http.Response(jsonEncode(wallet(hearts: 9)), 200);
      }),
    );
    final api = Api(MockClient((_) => slow.future));
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await t.pump(const Duration(milliseconds: 100));
    await t.pumpWidget(_wrap(const SizedBox())); // 홈으로(응답 전)
    slow.complete(http.Response('', 502)); // 결과 모름 — 재시도는 화면이 없어 멈춘다
    await t.pump(const Duration(seconds: 2));
    expect(gets, greaterThan(0));
    expect(Wallet.current.value?.hearts, 9);
  });

  testWidgets('새 판을 받았어도 나눠 주기 연출 중에 닫으면 id를 남기고, 다 보이면 지운다', (t) async {
    final api = Api(MockClient((_) async => http.Response(jsonEncode(view()), 200)));
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await t.pump(const Duration(milliseconds: 300)); // 응답은 왔고 연출 중
    expect(Api.pendingNewGame, isNotEmpty);
    await t.pumpWidget(_wrap(const SizedBox())); // 연출 중에 홈으로
    await t.pump(const Duration(seconds: 5));
    expect(Api.pendingNewGame, isNotEmpty); // 다음 진입이 같은 판을 받는다

    Api.pendingNewGame.clear();
    final api2 = Api(MockClient((_) async => http.Response(jsonEncode(view()), 200)));
    await t.pumpWidget(_wrap(TableScreen(api: api2, showHelpOnFirstVisit: false)));
    await settle(t);
    expect(Api.pendingNewGame, isEmpty);
  });

  test('세션 갱신 뒤 다시 보내기 전에 화면이 닫혔으면 새 판을 다시 보내지 않는다', () async {
    var games = 0;
    var open = true;
    final c = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/refresh') {
          open = false; // 갱신하는 사이 홈으로
          return http.Response(jsonEncode({'access': 'A2', 'refresh': 'r2'}), 200);
        }
        games++;
        return http.Response('{"detail":{"code":"session"}}', 401);
      }),
    )..keep({'access': 'A', 'refresh': 'r'});
    final api = Api(c)..wanted = (() => open);
    await expectLater(api.newGame(), throwsA(anything));
    expect(games, 1);
  });

  testWidgets('출석 결과를 모르면(503) 잔고를 다시 받는다', (t) async {
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/wallet/attend') return http.Response('', 503);
        gets++;
        return http.Response(jsonEncode(wallet(claimed: gets > 1)), 200);
      }),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('attend')));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.attended, isTrue);
  });

  test('보내기 직전에 원하지 않게 된 요청(닫힌 판 화면)은 보내지 않는다', () async {
    var sent = 0;
    final c = AuthClient(
      MockClient((_) async {
        sent++;
        return http.Response('{}', 200);
      }),
    );
    await expectLater(c.send(GuardedRequest('POST', Uri.parse('https://k/api/games'), () => false)), throwsA(anything));
    expect(sent, 0);
  });

  testWidgets('나눠 주기 뒤 봇 수를 재생하는 중에 닫아도 새 판 id를 남긴다', (t) async {
    final v = view(
      events: [
        for (final seat in [1, 2, 3])
          {
            'seat': seat,
            'tiles': ['c4'],
          },
      ],
    );
    final api = Api(MockClient((_) async => http.Response(jsonEncode(v), 200)));
    await t.pumpWidget(_wrap(TableScreen(api: api, showHelpOnFirstVisit: false)));
    await t.pump(const Duration(milliseconds: 3000)); // 나눠 주기(약 2.3초)는 끝났고 봇 수 재생 중(1.2초씩 3번)
    await t.pumpWidget(_wrap(const SizedBox()));
    await t.pump(const Duration(seconds: 5));
    expect(Api.pendingNewGame, isNotEmpty);
  });

  testWidgets('출석 결과를 모르는 채 미션 화면을 닫았어도 잔고를 다시 받는다', (t) async {
    final slow = Completer<http.Response>();
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((r) {
        if (r.url.path == '/api/wallet/attend') return slow.future;
        gets++;
        return Future.value(http.Response(jsonEncode(wallet(claimed: gets > 1)), 200));
      }),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('attend')));
    await t.pump();
    await t.pumpWidget(_wrap(const SizedBox()));
    slow.complete(http.Response('', 503));
    await t.pumpAndSettle();
    expect(Wallet.current.value?.attended, isTrue);
  });

  test('로그아웃이 서버에 닿지 못하면(연결 오류) 로그아웃된 척하지 않고 실패를 알린다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(MockClient((_) async => throw http.ClientException('offline')));
    await expectLater(Auth.logout(), throwsA(anything));
    expect(Auth.me.value?.id, 1);
  });

  testWidgets('하트 부족 뒤 잔고 받기가 실패하면 30초 뒤 다시 받는다', (t) async {
    var gets = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        gets++;
        if (gets == 2) return http.Response('', 503);
        return http.Response(jsonEncode(wallet(hearts: gets > 2 ? 0 : 10, next: gets > 2 ? 4e9 : null)), 200);
      }),
    );
    final api = Api(MockClient((_) async => http.Response('{"detail":{"code":"no_heart"}}', 402)));
    await t.pumpWidget(
      _wrap(
        Stack(
          children: [
            TableScreen(api: api, showHelpOnFirstVisit: false),
            const Material(child: WalletBar()),
          ],
        ),
      ),
    );
    await t.pump(const Duration(seconds: 1));
    await t.pump(const Duration(seconds: 31));
    await t.pump(const Duration(seconds: 1));
    expect(Wallet.current.value?.hearts, 0);
  });

  test('멈춘 갱신은 제한 시간에 끊기고, 다음 갱신은 같은 옛 토큰으로 다시 받는다(서버 멱등) — 늦은 응답은 버림', () async {
    var stall = true;
    final sent = <String>[];
    final auth = <String?>[];
    final c =
        AuthClient(
            MockClient((r) {
              if (r.url.path == '/api/auth/refresh') {
                final j = jsonDecode(r.body);
                sent.add('${j['refresh']}/${j['retry']}');
                if (stall) {
                  stall = false;
                  return Future.delayed(
                    const Duration(milliseconds: 200),
                    () => http.Response(jsonEncode({'access': 'LATE', 'refresh': 'rLATE'}), 200),
                  );
                }
                return Future.value(http.Response(jsonEncode({'access': 'A2', 'refresh': 'rA2'}), 200));
              }
              auth.add(r.headers['authorization']);
              return Future.value(http.Response('{}', 200));
            }),
          )
          ..timeout = const Duration(milliseconds: 50)
          ..keep({'access': 'A', 'refresh': 'rA'});
    await expectLater(c.refresh(), throwsA(isA<TimeoutException>()));
    expect(await c.refresh(), isTrue);
    // 끊긴 뒤에도 옛 토큰과 같은 재시도 키 그대로 — 서버가 같은 새 토큰을 다시 준다
    expect(sent.map((e) => e.split('/')[0]), ['rA', 'rA']);
    expect(sent[0].split('/')[1], hasLength(greaterThan(20)));
    expect(sent[1], sent[0]);
    await c.refresh(); // 응답을 받은 뒤의 갱신은 새 키
    expect(sent[2].split('/')[1], isNot(sent[0].split('/')[1]));
    await Future<void>.delayed(const Duration(milliseconds: 250)); // 끊긴 요청의 늦은 응답
    await c.get(Uri.parse('https://k/api/wallet'));
    expect(auth.last, 'Bearer A2');
  });

  testWidgets('2단계 인증 화면의 로그아웃이 서버에 닿지 못하면 알린다', (t) async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a', 'mfa_enabled': true, 'mfa_passed': false});
    Auth.client = AuthClient(MockClient((_) async => throw http.ClientException('offline')));
    await t.pumpWidget(_wrap(const MfaScreen()));
    await t.pumpAndSettle();
    await t.tap(find.text('Log out'));
    await t.pumpAndSettle();
    expect(find.text("Couldn't reach the server. Try again."), findsOneWidget);
    expect(Auth.me.value?.id, 1);
  });

  test('앱: 늦게 온 A의 갱신 응답은 그사이 로그인한 B의 토큰을 덮거나 지우지 않는다', () async {
    for (final late in [
      http.Response(jsonEncode({'access': 'A2', 'refresh': 'rA2'}), 200),
      http.Response('{"detail":{"code":"session"}}', 401),
    ]) {
      final slow = Completer<http.Response>();
      final auth = <String?>[];
      final c =
          AuthClient(
              MockClient((r) {
                if (r.url.path == '/api/auth/refresh') return slow.future;
                auth.add(r.headers['authorization']);
                return Future.value(http.Response('{}', 200));
              }),
            )
            ..timeout = const Duration(milliseconds: 50)
            ..keep({'access': 'A', 'refresh': 'rA'});
      await expectLater(c.refresh(), throwsA(isA<TimeoutException>()));
      c.keep(null); // 로그아웃
      c.keep({'access': 'B', 'refresh': 'rB'}); // B로 로그인
      slow.complete(late);
      await Future<void>.delayed(const Duration(milliseconds: 10));
      await c.get(Uri.parse('https://k/api/wallet'));
      expect(auth.last, 'Bearer B');
    }
  });

  test('앱: 멈춘 A의 갱신이 그 뒤 로그인한 B의 갱신을 막지 않는다', () async {
    final sent = <String>[];
    final c =
        AuthClient(
            MockClient((r) {
              final tok = jsonDecode(r.body)['refresh'] as String;
              sent.add(tok);
              if (tok == 'rA') return Completer<http.Response>().future; // A의 갱신은 멈춤
              return Future.value(http.Response(jsonEncode({'access': 'B2', 'refresh': 'rB2'}), 200));
            }),
          )
          ..timeout = const Duration(milliseconds: 50)
          ..keep({'access': 'A', 'refresh': 'rA'});
    await expectLater(c.refresh(), throwsA(isA<TimeoutException>()));
    c.keep(null);
    c.keep({'access': 'B', 'refresh': 'rB'});
    expect(await c.refresh(), isTrue);
    expect(sent, ['rA', 'rB']);
  });

  test('계정을 다시 읽는 사이 직접 로그인했다 로그아웃해도 늦은 응답으로 그 계정을 되살리지 않는다', () async {
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(MockClient((_) => slow.future));
    final pending = Auth.reloadAfterSwitch();
    Auth.me.value = Me.fromJson({'id': 2, 'nickname': 'b'}); // B로 로그인
    Auth.me.value = null; // 로그아웃
    slow.complete(http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200));
    await pending;
    expect(Auth.me.value, isNull);
  });

  test('로그아웃에도 화면의 계정 번호를 붙여, 다른 탭이 B로 바꿨으면 B의 세션을 폐기하지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final sent = <String?>[];
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/logout') {
          sent.add(r.headers['x-kumoniji-account']);
          return http.Response('{"detail":{"code":"account_changed"}}', 409);
        }
        return http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200);
      }),
    );
    await Auth.logout();
    expect(sent, ['1']);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(Auth.me.value?.id, 2); // 로그아웃된 척하지 않고 지금 쿠키의 계정(B)을 읽음
  });

  test('로그아웃 응답을 기다리는 사이 다시 로그인했으면 늦은 성공 응답이 새 로그인을 지우지 않는다(리뷰 52차)', () async {
    final slow = Completer<http.Response>();
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(
      MockClient(
        (r) => r.url.path == '/api/auth/logout'
            ? slow.future
            : Future.value(http.Response('{"id":1,"nickname":"a"}', 200)),
      ),
    );
    final out = Auth.logout();
    await Future<void>.delayed(Duration.zero);
    final again = Me.fromJson({'id': 1, 'nickname': 'a'}); // 먼저 온 다른 로그아웃 뒤 다시 로그인
    Auth.me.value = null;
    await Auth.load(); // 다시 로그인하면 로그인 상태를 처음부터 읽는다
    Auth.me.value = again;
    slow.complete(http.Response('{"status":"ok"}', 200));
    await out;
    expect(Auth.me.value, same(again));
  });

  test('로그아웃과 겹친 같은 세션의 내 정보 다시 읽기는 로그아웃을 막지 않는다(리뷰 54차)', () async {
    final slow = Completer<http.Response>();
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(MockClient((_) => slow.future))..keep({'access': 'A', 'refresh': 'rA'});
    final out = Auth.logout();
    await Future<void>.delayed(Duration.zero);
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a2'}); // 다시 읽기가 새 객체로 바꿈
    slow.complete(http.Response('{"status":"ok"}', 200));
    await out;
    expect(Auth.me.value, isNull);
  });

  test('로그아웃이 만료(401) 말고 다른 이유로 거절되면(CSRF 403 등) 로그아웃된 척하지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(MockClient((_) async => http.Response('{"detail":{"code":"csrf"}}', 403)));
    await expectLater(Auth.logout(), throwsA(isA<AuthError>()));
    expect(Auth.me.value?.id, 1);
  });

  test('갱신이 429(요청 제한)여도 세션이 끝난 게 아니다 — 토큰을 지우지 않는다(리뷰 53차)', () async {
    final auth = <String?>[];
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/refresh') return http.Response('{"detail":{"code":"busy","seconds":5}}', 429);
        auth.add(r.headers['authorization']);
        return http.Response('{}', 200);
      }),
    )..keep({'access': 'A', 'refresh': 'rA'});
    await expectLater(Auth.client.refresh(), throwsA(anything));
    await Auth.client.get(Uri.parse('https://k/api/wallet'));
    expect(auth.last, 'Bearer A'); // 토큰은 그대로
  });

  test('갱신이 5xx면 세션이 끝난 게 아니다 — 토큰을 지우지 않고, 로그아웃도 성공한 척하지 않는다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    final auth = <String?>[];
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/refresh') return http.Response('', 503);
        auth.add(r.headers['authorization']);
        if (r.url.path == '/api/auth/logout') return http.Response('{"detail":{"code":"session"}}', 401);
        return http.Response('{}', 200);
      }),
    )..keep({'access': 'A', 'refresh': 'rA'});
    await expectLater(Auth.logout(), throwsA(anything));
    expect(Auth.me.value?.id, 1);
    await Auth.client.get(Uri.parse('https://k/api/wallet'));
    expect(auth.last, 'Bearer A'); // 토큰은 그대로
  });

  test('로그아웃이 401이면 서버가 갱신을 거절할 때만 로그아웃 상태로 — 갱신됨·다른 탭 갱신(409)·장애면 실패로 알린다', () async {
    for (final (refresh, out) in [
      (http.Response(jsonEncode({'access': 'A2', 'refresh': 'rA2'}), 200), false),
      (http.Response('{"code":"rotated"}', 409), false),
      (http.Response('{"detail":{"code":"busy"}}', 503), false),
      (http.Response('{"code":"session"}', 401), true),
    ]) {
      Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
      Auth.client =
          AuthClient(
              MockClient((r) async {
                if (r.url.path == '/api/auth/refresh') return refresh;
                return http.Response('{"detail":{"code":"session"}}', 401);
              }),
            )
            ..raceWait = Duration.zero
            ..keep({'access': 'A', 'refresh': 'rA'});
      if (out) {
        await Auth.logout();
        expect(Auth.me.value, isNull, reason: '${refresh.statusCode}');
      } else {
        await expectLater(Auth.logout(), throwsA(anything), reason: '${refresh.statusCode}');
        expect(Auth.me.value?.id, 1, reason: '${refresh.statusCode}');
      }
    }
  });

  test('앱: 멈춘 A의 갱신 응답이 그 뒤 로그인한 B의 재시도 키를 지우지 않는다', () async {
    final keys = <String, List<String>>{};
    final slowA = Completer<http.Response>();
    var bFirst = true;
    final c =
        AuthClient(
            MockClient((r) {
              final j = jsonDecode(r.body);
              (keys[j['refresh'] as String] ??= []).add(j['retry'] as String);
              if (j['refresh'] == 'rA') return slowA.future;
              if (bFirst) {
                bFirst = false;
                return Future.value(http.Response('', 504)); // B의 갱신은 결과 모름
              }
              return Future.value(http.Response(jsonEncode({'access': 'B2', 'refresh': 'rB2'}), 200));
            }),
          )
          ..timeout = const Duration(milliseconds: 200)
          ..keep({'access': 'A', 'refresh': 'rA'});
    final a = c.refresh();
    c.keep({'access': 'B', 'refresh': 'rB'});
    await expectLater(c.refresh(), throwsA(isA<http.ClientException>()));
    slowA.complete(http.Response(jsonEncode({'access': 'A2', 'refresh': 'rA2'}), 200)); // A의 응답이 늦게
    await a;
    await c.refresh();
    expect(keys['rB']![1], keys['rB']![0]);
  });

  test('갱신이 5xx(프록시 504 등)면 결과를 모르니 다음 갱신도 같은 재시도 키로 보낸다', () async {
    final keys = <String>[];
    var first = true;
    final c = AuthClient(
      MockClient((r) async {
        keys.add(jsonDecode(r.body)['retry'] as String);
        if (first) {
          first = false;
          return http.Response('', 504);
        }
        return http.Response(jsonEncode({'access': 'A2', 'refresh': 'rA2'}), 200);
      }),
    )..keep({'access': 'A', 'refresh': 'rA'});
    await expectLater(c.refresh(), throwsA(isA<http.ClientException>()));
    expect(await c.refresh(), isTrue);
    expect(keys[1], keys[0]);
  });

  test('갱신이 403(CSRF 거절)이면 처리 전 거절이니 토큰·로그인을 두고 다음 갱신도 같은 재시도 키로', () async {
    final keys = <String>[];
    final auth = <String?>[];
    var first = true;
    final c = AuthClient(
      MockClient((r) async {
        if (r.url.path != '/api/auth/refresh') {
          auth.add(r.headers['authorization']);
          return http.Response('{}', 200);
        }
        keys.add(jsonDecode(r.body)['retry'] as String);
        if (first) {
          first = false;
          return http.Response('{"detail":{"code":"csrf"}}', 403);
        }
        return http.Response(jsonEncode({'access': 'A2', 'refresh': 'rA2'}), 200);
      }),
    )..keep({'access': 'A', 'refresh': 'rA'});
    await expectLater(c.refresh(), throwsA(isA<http.ClientException>()));
    await c.get(Uri.parse('https://k/api/wallet'));
    expect(auth.last, 'Bearer A'); // 토큰을 지우지 않음
    expect(await c.refresh(), isTrue);
    expect(keys[1], keys[0]);
  });

  test('앱: 갱신이 200인데 본문이 깨졌으면 못 받은 것 — 토큰을 두고 다음 갱신도 같은 재시도 키로', () async {
    final keys = <String>[];
    var first = true;
    final c = AuthClient(
      MockClient((r) async {
        keys.add(jsonDecode(r.body)['retry'] as String);
        if (first) {
          first = false;
          return http.Response('', 200);
        }
        return http.Response(jsonEncode({'access': 'A2', 'refresh': 'rA2'}), 200);
      }),
    )..keep({'access': 'A', 'refresh': 'rA'});
    await expectLater(c.refresh(), throwsA(isA<http.ClientException>()));
    expect(await c.refresh(), isTrue);
    expect(keys[1], keys[0]);
  });

  test('지갑 401 뒤 갱신이 409(다른 탭이 방금 갱신)면 로그아웃하지 않고, 새 쿠키가 오면 다시 읽어 그대로 둔다', () async {
    final a = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.me.value = a;
    var meCalls = 0;
    Auth.client =
        AuthClient(
            MockClient((r) async {
              if (r.url.path == '/api/auth/refresh') return http.Response('{"code":"rotated"}', 409);
              if (r.url.path == '/api/auth/me') {
                return ++meCalls <= 1
                    ? http.Response('{"detail":{"code":"session"}}', 401)
                    : http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200);
              }
              return http.Response('{"detail":{"code":"session"}}', 401);
            }),
          )
          ..raceWait = Duration.zero
          ..keep({'access': 'A', 'refresh': 'rA'});
    await Wallet.refresh();
    expect(Auth.me.value?.id, 1); // 바로 로그아웃하지 않음
    await Future<void>.delayed(const Duration(milliseconds: 1500)); // 다시 읽기(1초 뒤)
    expect(Auth.me.value?.id, 1);
    expect(meCalls, 2);
  });

  test('시작 때 /me가 503이면 로그인 화면이되 뒤에서 다시 읽어 복구되면 로그인 상태로', () async {
    Auth.me.value = null;
    var down = true;
    Auth.client = AuthClient(
      MockClient(
        (r) async => down
            ? http.Response('{"detail":{"code":"busy"}}', 503)
            : http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200),
      ),
    );
    expect(await Auth.load(), isNull);
    down = false;
    await Future<void>.delayed(const Duration(milliseconds: 1500));
    expect(Auth.me.value?.id, 1);
  });

  test('계정 전환 복구 중 갱신이 409(다른 탭이 방금 갱신)이고 새 쿠키가 늦어도 그만두지 않고 다시 읽는다', () async {
    Auth.me.value = null;
    var meCalls = 0;
    Auth.client =
        AuthClient(
            MockClient((r) async {
              if (r.url.path == '/api/auth/refresh') return http.Response('{"code":"rotated"}', 409);
              return ++meCalls <= 2
                  ? http.Response('{"detail":{"code":"session"}}', 401)
                  : http.Response(jsonEncode({'id': 2, 'nickname': 'b'}), 200);
            }),
          )
          ..raceWait = Duration.zero
          ..keep({'access': 'A', 'refresh': 'rA'});
    final f = Auth.reloadAfterSwitch();
    await Future<void>.delayed(const Duration(milliseconds: 1500));
    await f;
    expect(Auth.me.value?.id, 2);
  });

  test('게임 요청의 401은 곧바로 로그아웃하지 않고 세션을 다시 확인 — 살아 있으면 그대로', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(MockClient((_) async => http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200)));
    final api = Api(MockClient((_) async => http.Response('{"detail":{"code":"session"}}', 401)));
    await expectLater(api.get('g1'), throwsA(isA<ApiError>()));
    expect(Auth.me.value?.id, 1);
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(Auth.me.value?.id, 1);
  });

  testWidgets('지갑 조회가 401이어도 세션이 살아 있으면 30초 뒤 다시 받는다', (t) async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/me') return http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200);
        return ++calls == 1
            ? http.Response('{"detail":{"code":"session"}}', 401)
            : http.Response(jsonEncode(wallet()), 200);
      }),
    );
    await t.pumpWidget(_wrap(const MissionsScreen()));
    await t.pump();
    await t.pump();
    expect(find.byKey(const ValueKey('attend')), findsNothing);
    await t.pump(const Duration(seconds: 31));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('attend')), findsOneWidget);
  });

  test('결과 모르는 일 뒤 지갑 받기가 401이어도 잔고 막대에 다시 받기를 알린다', () async {
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.client = AuthClient(
      MockClient(
        (r) async => r.url.path == '/api/auth/me'
            ? http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200)
            : http.Response('{"detail":{"code":"session"}}', 401),
      ),
    );
    final before = Wallet.retry.value;
    await Wallet.refreshOrRetry();
    expect(Wallet.retry.value, before + 1);
  });
}
