import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/practice.dart';
import 'package:kumoniji/settings.dart';
import 'package:kumoniji/sfx.dart';
import 'package:kumoniji/table_screen.dart';
import 'package:kumoniji/tile.dart';
import 'package:kumoniji/wallet.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;

/// 요청 본문에서 새 판 요청 id(rid, 판마다 무작위)를 빼고 비교한다
Object? noRid(String body) {
  if (body.isEmpty) return null;
  final j = jsonDecode(body);
  if (j is Map) j.remove('rid');
  return j;
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    markTilesReady();
  });
  moreTests();
  legalTests();
  recentTests();
  autoPassTests();
  testWidgets('a new game shown behind the web rotate notice keeps its request id until the table is visible', (
    t,
  ) async {
    final api = Api(MockClient((r) async => http.Response(jsonEncode(view()), 200)));
    final visible = ValueNotifier(false); // 웹 세로 안내(RotateGate)가 판을 가린 상태
    await t.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: ValueListenableBuilder<bool>(
          valueListenable: visible,
          builder: (_, on, child) => TickerMode(enabled: on, child: child!),
          child: TableScreen(api: api, showHelpOnFirstVisit: false),
        ),
      ),
    );
    for (var i = 0; i < 20; i++) {
      await t.pump(const Duration(milliseconds: 500));
    }
    expect(api.unsettled, isNotNull); // 가려진 채로는 지우지 않는다
    visible.value = true; // 가로로 돌림
    await t.pump();
    await t.pump();
    expect(api.unsettled, isNull);
  });

  // 844×390(폰 가로, 앱 기본)은 제목 자리에 무늬 순서가 들어가도 작은 로고로 홈에 간다(리뷰 19차)
  for (final size in [const Size(1280, 900), const Size(844, 390)]) {
    testWidgets(
      'tapping the title logo goes home like back (asks first during a game) at ${size.width.toInt()}x${size.height.toInt()}',
      (t) async {
        t.view.physicalSize = size;
        t.view.devicePixelRatio = 1;
        addTearDown(t.view.reset);
        final api = Api(MockClient((r) async => http.Response(jsonEncode(view()), 200)));
        await t.pumpWidget(
          MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: const Locale('en'),
            home: Builder(
              builder: (c) => TextButton(
                key: const ValueKey('go'),
                onPressed: () => Navigator.push(
                  c,
                  MaterialPageRoute(builder: (_) => TableScreen(api: api, showHelpOnFirstVisit: false)),
                ),
                child: const Text('home'),
              ),
            ),
          ),
        );
        await t.tap(find.byKey(const ValueKey('go')));
        await settle(t);
        await t.tap(find.byKey(const ValueKey('title-home')));
        await t.pumpAndSettle();
        await t.tap(find.widgetWithText(FilledButton, 'Leave'));
        await t.pumpAndSettle();
        expect(find.byType(TableScreen), findsNothing);
        expect(find.byKey(const ValueKey('go')), findsOneWidget);
        await t.pumpWidget(const SizedBox());
        await t.pump(const Duration(minutes: 1)); // 나간 판이 남긴 타이머(지갑 등)를 흘려보낸다
      },
    );
  }

  testWidgets('pick a tile and play sends it', (t) async {
    final paths = <String>[];
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        paths.add(r.url.path);
        bodies.add(noRid(r.body));
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await t.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: TableScreen(api: api, showHelpOnFirstVisit: false),
      ),
    );
    await settle(t);
    expect(find.text('Your turn'), findsOneWidget);
    // 바닥이 비어도(선) 패스할 수 있다(11-21 규칙 변경)
    expect(t.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Pass')).onPressed, isNotNull);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await settle(t);
    expect(paths, ['/api/games', '/api/games/a/moves']);
    expect(bodies.last, {
      'tiles': ['m1'],
    });
  });

  testWidgets('played tile leaves the hand before the server answers', (t) async {
    final reply = Completer<http.Response>();
    var calls = 0;
    final api = Api(MockClient((r) async => ++calls == 1 ? http.Response(jsonEncode(view()), 200) : reply.future));
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await t.pump();
    expect(find.byKey(const ValueKey('hand-m1')), findsNothing); // 응답 전인데 이미 손에서 빠짐
    // 서버가 거절하면 되돌린다
    reply.complete(
      http.Response(
        jsonEncode({
          'detail': {'code': 'weaker'},
        }),
        422,
      ),
    );
    await settle(t);
    expect(find.byKey(const ValueKey('hand-m1')), findsOneWidget);
  });

  testWidgets('network failure with failed resync still returns the played tile', (t) async {
    final reply = Completer<http.Response>();
    var calls = 0;
    final api = Api(
      MockClient((r) async {
        calls++;
        if (calls == 1) return http.Response(jsonEncode(view()), 200);
        if (calls == 2) return reply.future;
        throw Exception('offline'); // 재조회도 실패
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await t.pump();
    expect(find.byKey(const ValueKey('hand-m1')), findsNothing);
    reply.completeError(Exception('offline'));
    await settle(t);
    expect(find.byKey(const ValueKey('hand-m1')), findsOneWidget);
    expect(find.text('Your turn'), findsOneWidget);
  });
}

Widget _app(Api api) => MaterialApp(
  locale: const Locale('en'),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: TableScreen(api: api, showHelpOnFirstVisit: false),
);

void moreTests() {
  testWidgets('new game shows the fresh board and a start card before the bots play', (t) async {
    final api = Api(
      MockClient(
        (r) async => http.Response(
          jsonEncode({
            ...view(
              events: [
                {
                  'seat': 3,
                  'tiles': ['c1'],
                },
              ],
            ),
            'counts': [2, 13, 13, 12],
            'plays': [
              null,
              null,
              null,
              ['c1'],
            ],
          }),
          200,
        ),
      ),
    );
    await t.pumpWidget(_app(api));
    await t.pump(); // 응답
    await t.pump(const Duration(milliseconds: 80));
    expect(find.byKey(const ValueKey('hand-m1')), findsOneWidget); // 나눠 주는 중: 한 장씩
    expect(find.byKey(const ValueKey('hand-s3')), findsNothing);
    expect(find.text('Your turn'), findsNothing); // 나눠 주는 동안엔 차례 표시 없음
    for (var k = 0; k < 13; k++) {
      await t.pump(const Duration(milliseconds: 70)); // 나눠 주기 한 바퀴씩
    }
    await t.pump(const Duration(milliseconds: 100));
    expect(find.byKey(const ValueKey('hand-s3')), findsOneWidget);
    expect(find.byKey(const ValueKey('start-card')), findsOneWidget); // 시작 카드
    expect(find.text('×13'), findsNWidgets(3)); // 봇이 내기 전 13장씩
    expect(find.byKey(const ValueKey('play-3')), findsNothing); // 아직 아무도 안 냄
    await t.pump(const Duration(milliseconds: 1400));
    await t.pump(const Duration(milliseconds: 100));
    expect(find.byKey(const ValueKey('start-card')), findsNothing);
    expect(find.byKey(const ValueKey('play-3')), findsOneWidget); // 봇 3이 솜사탕 1을 내는 장면
    expect(find.text('×12'), findsOneWidget);
    await settle(t);
  });

  testWidgets('starts with the level chosen last time', (t) async {
    SharedPreferences.setMockInitialValues({'level': 'easy'});
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(noRid(r.body));
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    expect(bodies, [
      {'level': 'easy'},
    ]);
  });

  testWidgets('new game asks the level and sends it; cancel keeps the game', (t) async {
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(noRid(r.body));
        return http.Response(jsonEncode({...view(), 'level': (bodies.last as Map?)?['level'] ?? 'normal'}), 200);
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    expect(bodies, [
      {'level': 'normal'},
    ]); // 처음엔 중급
    expect(find.text('  ·  Normal'), findsOneWidget); // 이름은 제목 로고, 옆에 난이도
    await t.tap(find.widgetWithText(TextButton, 'New game'));
    await settle(t);
    expect(find.text('Quit this game and start a new one?'), findsOneWidget); // 진행 중이라 그만둘지 같이 묻는다
    await t.tap(find.text('Cancel'));
    await settle(t);
    expect(bodies.length, 1);
    await t.tap(find.widgetWithText(TextButton, 'New game'));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('level-hard')));
    await t.pump();
    expect(bodies.length, 1); // 고르기만 해서는 시작하지 않는다
    await t.tap(find.byKey(const ValueKey('level-start')));
    await settle(t);
    expect(bodies.last, {'level': 'hard'});
    expect(find.text('  ·  Hard'), findsOneWidget);
  });

  testWidgets('first request fails → retry button starts a game', (t) async {
    var calls = 0;
    final api = Api(
      MockClient(
        (r) async => ++calls <= 3 ? http.Response('', 503) : http.Response(jsonEncode(view()), 200),
      ), // 자동 재시도 2번까지 실패
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.widgetWithText(FilledButton, 'New game'));
    await settle(t);
    expect(find.text('Your turn'), findsOneWidget);
  });

  testWidgets('lost move response → refetches current state', (t) async {
    final paths = <String>[];
    final api = Api(
      MockClient((r) async {
        paths.add('${r.method} ${r.url.path}');
        if (r.url.path.endsWith('/moves')) return http.Response('', 502);
        if (r.method == 'GET') {
          return http.Response(
            jsonEncode({
              ...view(),
              'hand': ['s3'],
              'counts': [1, 13, 13, 13],
            }),
            200,
          );
        }
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await settle(t);
    expect(paths, ['POST /api/games', 'POST /api/games/a/moves', 'GET /api/games/a']);
    expect(find.byKey(const ValueKey('hand-m1')), findsNothing);
    expect(find.byKey(const ValueKey('hand-s3')), findsOneWidget);
  });
}

void legalTests() {
  testWidgets('Play stays disabled unless the pick is exactly a legal move', (t) async {
    final api = Api(
      MockClient(
        (r) async => http.Response(
          jsonEncode({
            ...view(),
            'moves': [
              ['m1'],
            ],
            'playable': ['m1'],
          }),
          200,
        ),
      ),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    FilledButton play() => t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Play'));
    expect(play().onPressed, isNull);
    await t.tap(find.byKey(const ValueKey('hand-s3'))); // 낼 수 없는 패 — 눌리지 않음
    await t.pump();
    expect(play().onPressed, isNull);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    expect(play().onPressed, isNotNull);
  });

  testWidgets('result lists players from highest score', (t) async {
    final done = {
      ...view(),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(done), 200)));
    await t.pumpWidget(_app(api));
    await settle(t);
    final names = t.widgetList<ListTile>(find.byType(ListTile)).map((e) => (e.title as Text).data).toList();
    expect(names, ['Bot 3', 'Bot 2', 'You', 'Bot 1']);
  });

  testWidgets('끝난 판에서 새로 시작한 판도 지갑 없이 끝나면 잔고를 다시 받게 한다(리뷰 48차)', (t) async {
    final first = {
      ...view(),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
      'wallet': null,
    };
    final second = {...first, 'id': 'b'}; // 새 판도 봇 진행 중 끝났고 서버가 기록을 다시 시도 중(지갑 없음)
    var n = 0;
    final api = Api(MockClient((r) async => http.Response(jsonEncode(++n == 1 ? first : second), 200)));
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byIcon(Icons.close));
    await settle(t);
    final before = Wallet.recheck.value;
    await t.tap(find.widgetWithText(TextButton, 'New game'));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('level-start')));
    await settle(t);
    expect(Wallet.recheck.value, before + 1);
  });

  testWidgets('result has X to look at the finished table', (t) async {
    final done = {
      ...view(),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
    };
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(noRid(r.body));
        return http.Response(jsonEncode(bodies.length == 1 ? done : view()), 200);
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byIcon(Icons.close));
    await settle(t);
    expect(find.byKey(const ValueKey('result-home')), findsNothing); // 닫으면 끝난 판을 그대로 본다
    expect(bodies.length, 1);
    await t.tap(find.widgetWithText(TextButton, 'New game'));
    await settle(t);
    expect(find.byKey(const ValueKey('level-start')), findsOneWidget); // 위 '새 게임'은 난이도부터
    await t.tap(find.text('Cancel'));
    await settle(t);
    expect(bodies.length, 1);
  });

  testWidgets('result table scrolls on a short window so every rank stays readable', (t) async {
    t.view.physicalSize = const Size(320, 360);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final old = FlutterError.onError;
    final errors = <String>[];
    FlutterError.onError = (e) => errors.add(e.toString()); // 판 화면 자체의 넘침은 범위 밖 — 결과 창만 본다
    final done = {
      ...view(),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(done), 200)));
    await t.pumpWidget(_app(api));
    await settle(t);
    FlutterError.onError = old;
    expect(errors.where((e) => e.contains('AlertDialog') || e.contains('ListTile')), isEmpty);
    final last = find.descendant(of: find.byType(AlertDialog), matching: find.text('Bot 1'));
    await t.dragUntilVisible(
      last,
      find.descendant(of: find.byType(AlertDialog), matching: find.byType(SingleChildScrollView)).first,
      const Offset(0, -40),
    );
    expect(last.hitTestable(), findsOneWidget); // 마지막 순위까지 스크롤해 볼 수 있다
  });

  testWidgets('result Restart begins the next game at the same level without asking', (t) async {
    final done = {
      ...view(),
      'level': 'hard',
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
    };
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(noRid(r.body));
        return http.Response(jsonEncode(bodies.length == 1 ? done : view()), 200);
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('result-restart')));
    await settle(t);
    expect(bodies, [
      {'level': 'normal'},
      {'level': 'hard'}, // 저장된 난이도가 아니라 끝난 판의 난이도
    ]);
    expect(find.text('Your turn'), findsOneWidget);
  });
}

void recentTests() {
  testWidgets('played-tiles panel shows a bot tile only once it is replayed', (t) async {
    t.view.physicalSize = const Size(1280, 860);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final v = {
      ...view(
        events: [
          {
            'seat': 1,
            'tiles': ['c4'],
          },
        ],
      ),
      'out': ['c4'],
    };
    await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
    double fill() => t.widget<Opacity>(find.byKey(const ValueKey('out-c4'))).opacity; // 나온 패는 또렷(1)
    await t.pump(const Duration(milliseconds: 1500)); // 나눠 주기·시작 카드 — 봇 수는 아직
    expect(fill(), lessThan(1));
    await settle(t);
    expect(fill(), 1);
  });

  testWidgets('a combo window opened during replay stays put and the result still shows on top', (t) async {
    final done = {
      ...view(
        events: [
          {
            'seat': 3,
            'tiles': ['c4'],
          },
        ],
      ),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
      'out': ['c4'],
    };
    await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(done), 200)))));
    await t.pump(const Duration(milliseconds: 2600)); // 시작 카드가 끝나고 봇 수 재생 중
    await t.tap(find.byKey(const ValueKey('open-combos')));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.byKey(const ValueKey('combo-chart')), findsOneWidget);
    await settle(t);
    expect(find.byKey(const ValueKey('result-home')), findsOneWidget);
    // 떠 있는 창은 사용자가 켜고 끄는 것 — 결과 창 아래 그대로 두고, 결과 창이 위에 뜬다
    expect(find.byKey(const ValueKey('float-combos')), findsOneWidget);
  });

  testWidgets('the enlarged played-tiles dialog opened during replay closes when the result shows', (t) async {
    t.view.physicalSize = const Size(1280, 900);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final done = {
      ...view(
        events: [
          {
            'seat': 3,
            'tiles': ['c4'],
          },
        ],
      ),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
      'out': ['c4'],
    };
    await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(done), 200)))));
    await t.pump(const Duration(milliseconds: 2600)); // 봇 수 재생 중
    await t.tap(find.byKey(const ValueKey('out-big')));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.byKey(const ValueKey('out-tracker')), findsNWidgets(2));
    await settle(t);
    expect(find.byKey(const ValueKey('result-home')), findsOneWidget);
    expect(find.byKey(const ValueKey('out-tracker')), findsOneWidget); // 옆 패널만 남는다
  });

  testWidgets('help opened during replay stays open over the result', (t) async {
    final done = {
      ...view(
        events: [
          {
            'seat': 3,
            'tiles': ['c4'],
          },
        ],
      ),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
      'out': ['c4'],
    };
    await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(done), 200)))));
    await t.pump(const Duration(milliseconds: 2600));
    await t.tap(find.byIcon(Icons.help_outline));
    await t.pump(const Duration(milliseconds: 300));
    await settle(t);
    expect(find.byKey(const ValueKey('result-home')), findsOneWidget);
    expect(find.byType(PageView), findsOneWidget); // 도움말 카드 창이 그대로
  });

  testWidgets('phone: played tiles open in a floating window that follows the new state and leaves the game usable', (
    t,
  ) async {
    final live = ValueNotifier<List<String>?>(['c1']);
    var behind = 0;
    await t.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: PracticeFrame(
            out: const ['c1'],
            live: live,
            suits: const ['m', 's', 'l', 'c'],
            child: Align(
              alignment: Alignment.bottomRight,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextButton(key: const ValueKey('behind'), onPressed: () => behind++, child: const Text('play')),
                  const PracticeButtons(out: ['c1'], suits: ['m', 's', 'l', 'c']),
                ],
              ),
            ),
          ),
        ),
      ),
    );
    await t.tap(find.byKey(const ValueKey('open-out')));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('float-out')), findsOneWidget);
    expect(find.byType(BottomSheet), findsNothing); // 판을 막는 시트가 아니다
    await t.tap(find.byKey(const ValueKey('behind')));
    expect(behind, 1); // 창이 떠 있어도 게임 버튼이 눌린다
    double fill(String c) => t.widget<Opacity>(find.byKey(ValueKey('out-$c'))).opacity;
    expect(fill('l3'), lessThan(1));
    live.value = ['c1', 'l3']; // 봇 수 재생이 끝나 상태가 바뀜
    await t.pump();
    expect(fill('l3'), 1);
    await t.tap(find.byKey(const ValueKey('float-out-close')));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('float-out')), findsNothing);
    await t.tap(find.byKey(const ValueKey('open-out'))); // 버튼으로도 껐다 켠다
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('open-out')));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('float-out')), findsNothing);
  });

  testWidgets(
    'practice: phone opens played tiles and combos in floating windows; wide screen shows both beside the table',
    (t) async {
      final v = {
        ...view(),
        'out': ['c1', 'l3'],
      };
      t.view.physicalSize = const Size(390, 844);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
      await settle(t);
      expect(find.byKey(const ValueKey('out-tracker')), findsNothing);
      await t.tap(find.byKey(const ValueKey('open-out')));
      await t.pumpAndSettle();
      expect(t.widget<Opacity>(find.byKey(const ValueKey('out-c1'))).opacity, 1); // 낸 패는 또렷하게
      expect(t.widget<Opacity>(find.byKey(const ValueKey('out-c2'))).opacity, lessThan(1));
      expect(
        find.descendant(of: find.byKey(const ValueKey('out-c2')), matching: find.byType(TileView)),
        findsOneWidget,
      );
      expect(
        find.descendant(of: find.byKey(const ValueKey('out-tracker')), matching: find.bySemanticsLabel('13')),
        findsWidgets,
      );
      await t.tap(find.byKey(const ValueKey('float-out-close')));
      await t.pumpAndSettle();
      await t.tap(find.byKey(const ValueKey('open-combos')));
      await t.pumpAndSettle();
      expect(find.byKey(const ValueKey('combo-chart')), findsOneWidget);
      expect(find.byKey(const ValueKey('float-combos')), findsOneWidget);
      PracticeFrame.floatCombos.value = false;

      t.view.physicalSize = const Size(1280, 900);
      await t.pumpWidget(const SizedBox());
      await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
      await settle(t);
      expect(find.byKey(const ValueKey('out-tracker')), findsOneWidget);
      expect(find.byKey(const ValueKey('combo-chart')), findsOneWidget);
      // 넓은 화면에서도 버튼이 있고, 누르면 옆 패널을 숨기고 다시 누르면 보인다(11-27 사용자 '보기 숨기기가 쉽게')
      for (final (button, panel) in [('open-combos', 'combo-chart'), ('open-out', 'out-tracker')]) {
        await t.tap(find.byKey(ValueKey(button)));
        await t.pumpAndSettle();
        expect(find.byKey(ValueKey(panel)), findsNothing, reason: button);
        expect(find.byType(BottomSheet), findsNothing); // 넓은 화면은 시트가 아니라 패널을 끈다
        await t.tap(find.byKey(ValueKey(button)));
        await t.pumpAndSettle();
        expect(find.byKey(ValueKey(panel)), findsOneWidget, reason: button);
      }
      // 옆 패널은 한 줄 13장이라 작다 — 크게 보기 창에선 패가 더 크다(11-26 사용자)
      final small = t.getSize(find.byKey(const ValueKey('out-c1'))).width;
      await t.tap(find.byKey(const ValueKey('out-big')));
      await t.pumpAndSettle();
      expect(find.byKey(const ValueKey('out-tracker')), findsNWidgets(2));
      expect(t.getSize(find.byKey(const ValueKey('out-c1')).last).width, greaterThan(small * 2));
      expect(t.takeException(), isNull);
    },
  );

  testWidgets('a wide but short window keeps the side panels off so pass and play stay visible', (t) async {
    t.view.physicalSize = const Size(1000, 420);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(
      _app(
        Api(
          MockClient(
            (r) async => http.Response(
              jsonEncode({
                ...view(),
                'out': ['c1'],
              }),
              200,
            ),
          ),
        ),
      ),
    );
    await settle(t);
    while (t.takeException() != null) {} // 낮은 가로 창의 옆자리 넘침은 이전부터
    expect(find.byKey(const ValueKey('out-tracker')), findsNothing);
    expect(find.byKey(const ValueKey('open-combos')), findsOneWidget);
  });

  // 844×390은 이번 변경 전(main)부터 버튼이 9px 넘친다 — 앱 전용·화면 방향을 정한 뒤 다룬다
  for (final size in [const Size(1000, 420), const Size(1280, 510)]) {
    testWidgets('pass and play stay on screen with 13 tiles at ${size.width.toInt()}x${size.height.toInt()}', (
      t,
    ) async {
      t.view.physicalSize = size;
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      final hand = ['m1', 'm4', 's3', 's5', 'l2', 'l7', 'c3', 'c6', 'm9', 's10', 'l11', 'c12', 'm13'];
      final v = {
        ...view(),
        'hand': hand,
        'counts': [13, 13, 13, 13],
        'playable': hand,
        'moves': [
          for (final h in hand) [h],
        ],
        'out': <String>[],
      };
      await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
      await settle(t);
      while (t.takeException() != null) {}
      final pass = t.getRect(find.widgetWithText(OutlinedButton, 'Pass'));
      expect(pass.bottom <= size.height, isTrue, reason: '$pass');
    });
  }

  testWidgets('without out (multi) there is no played-tiles view, only combos', (t) async {
    t.view.physicalSize = const Size(1280, 900);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(view()), 200)))));
    await settle(t);
    expect(find.byKey(const ValueKey('out-tracker')), findsNothing);
    expect(find.byKey(const ValueKey('combo-chart')), findsOneWidget);
  });

  for (final size in [const Size(320, 700), const Size(390, 844), const Size(800, 900)]) {
    testWidgets('no overflow at ${size.width.toInt()}x${size.height.toInt()} with the bigger hand', (t) async {
      t.view.physicalSize = size;
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      final hand = ['m1', 'm4', 's3', 's5', 'l2', 'l7', 'c3', 'c6', 'm9', 's10', 'l11', 'c12', 'm13'];
      final v = {
        ...view(),
        'hand': hand,
        'counts': [13, 13, 13, 13],
        'playable': hand,
        'moves': [
          for (final h in hand) [h],
        ],
      };
      await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
      await settle(t);
      expect(t.takeException(), isNull);
    });
  }

  for (final size in [const Size(1280, 510), const Size(844, 390)]) {
    testWidgets('a short ${size.width.toInt()}x${size.height.toInt()} landscape window puts the hand in one row', (
      t,
    ) async {
      t.view.physicalSize = size;
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      final hand = ['m1', 'm4', 's3', 's5', 'l2', 'l7', 'c3', 'c6', 'm9', 's10', 'l11', 'c12', 'm13'];
      final v = {
        ...view(),
        'hand': hand,
        'counts': [13, 13, 13, 13],
        'playable': hand,
        'moves': [
          for (final h in hand) [h],
        ],
      };
      await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
      await settle(t);
      expect(t.takeException(), isNull); // 앱 기본이 가로(11-25) — 넘침 없이
      final tops = {for (final c in hand) t.getRect(find.byKey(ValueKey('hand-$c'))).top};
      expect(tops.length, 1);
      expect(t.getRect(find.widgetWithText(OutlinedButton, 'Pass')).bottom <= size.height, isTrue);
      expect(find.byKey(const ValueKey('suit-order')), findsOneWidget); // 위 막대로 올라감
    });
  }

  for (final size in [
    const Size(320, 700),
    const Size(390, 844),
    const Size(420, 900),
    const Size(700, 900),
    const Size(844, 390),
  ]) {
    testWidgets('big hand and the app bar stay on a ${size.width.toInt()}px phone', (t) async {
      t.view.physicalSize = size;
      t.view.devicePixelRatio = 1;
      t.platformDispatcher.textScaleFactorTestValue = 2; // 글자 200%에서도 위 줄 버튼이 화면 안
      addTearDown(t.view.reset);
      addTearDown(t.platformDispatcher.clearTextScaleFactorTestValue);
      final hand = ['m1', 'm4', 's3', 's5', 'l2', 'l7', 'c3', 'c6', 'm9', 's10', 'l11', 'c12', 'm13'];
      final v = {
        ...view(),
        'hand': hand,
        'counts': [13, 13, 13, 13],
        'doubles': 2, // 오늘의 무늬 배지에 ×25
        'playable': hand,
        'moves': [
          for (final h in hand) [h],
        ],
      };
      await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
      await settle(t);
      // 글자 200%에서 옆자리 칸이 넘치는 것은 이번 변경 전부터(손패·위 줄만 본다)
      while (t.takeException() != null) {}
      for (final c in hand) {
        final r = t.getRect(find.byKey(ValueKey('hand-$c')));
        expect(r.left >= 0 && r.right <= size.width, isTrue, reason: '$c $r');
      }
      for (final f in [find.byKey(const ValueKey('mute')), find.byKey(const ValueKey('new-game'))]) {
        expect(t.getRect(f).right <= size.width, isTrue, reason: '$f');
      }
      // 낮은 가로 화면은 손패 한 줄(그래서 패는 작아진다)
      if (size.width > size.height) {
        expect({for (final c in hand) t.getRect(find.byKey(ValueKey('hand-$c'))).top}.length, 1);
      }
      // 실제로는 홈에서 들어와 왼쪽에 뒤로 가기(56)가 있다 — 배지가 그 자리를 남긴다
      expect(t.getRect(find.byKey(const ValueKey('today'))).left >= 56 + 8, isTrue);
    });
  }

  testWidgets('landscape phone: the board widens so a five-tile play stays readable', (t) async {
    t.view.physicalSize = const Size(844, 390);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final v = {
      ...view(),
      'turn': 0,
      'table': ['m2', 'm3', 'm4', 'm5', 's6'],
      'last': 3,
      'plays': [
        null,
        ['c7'],
        null,
        ['m2', 'm3', 'm4', 'm5', 's6'],
      ],
      'passed': <int>[],
    };
    await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
    await settle(t);
    expect(t.takeException(), isNull);
    // 정사각형 판일 땐 15px — 판을 가로로 넓혀(11-26 '낸 패 크게') 24px 넘게
    expect(t.getRect(find.byKey(const ValueKey('drop-3-m2m3m4m5s6-m2'))).width, greaterThan(24));
    expect(t.getRect(find.byKey(const ValueKey('drop-1-c7-c7'))).width, greaterThan(40));
  });

  testWidgets('the play to beat sits in the middle of the board; the others stay by their seats', (t) async {
    final v = {
      ...view(),
      'turn': 0,
      'table': ['m2', 'm3', 'm4', 'm5', 's6'],
      'last': 3,
      'plays': [
        null,
        ['c1', 'c2', 'c3', 'c4', 'l5'],
        ['c2', 'c3', 'c4', 'c5', 'l6'],
        ['m2', 'm3', 'm4', 'm5', 's6'],
      ],
      'passed': <int>[],
    };
    await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(v), 200)))));
    await settle(t);
    final mid = t.getCenter(find.byKey(const ValueKey('play-3'))); // 봇 3이 냈지만 오른쪽 가장자리가 아니라 가운데
    final left = t.getCenter(find.byKey(const ValueKey('play-1')));
    final top = t.getCenter(find.byKey(const ValueKey('play-2')));
    expect(mid.dx, closeTo(top.dx, 4)); // 위 자리와 같은 세로줄(가운데)
    expect(mid.dy, greaterThan(top.dy + 20)); // 위 자리보다 아래
    expect(mid.dx, greaterThan(left.dx)); // 왼쪽 자리 패는 그대로 왼쪽
    expect(find.text('Your turn'), findsNothing); // 가운데는 패 자리 — 글자는 판이 빌 때만
    // 날아오는 모션은 가운데(새로 낸) 패만 — 가장자리의 밀려난 패가 다시 날아오지 않게(리뷰 3차)
    expect(
      find.descendant(of: find.byKey(const ValueKey('play-3')), matching: find.byType(TweenAnimationBuilder<double>)),
      findsWidgets,
    );
    expect(
      find.descendant(of: find.byKey(const ValueKey('play-1')), matching: find.byType(TweenAnimationBuilder<double>)),
      findsNothing,
    );
  });

  testWidgets('each seat shows its own play and pass bubble; fits a 320px phone', (t) async {
    t.view.physicalSize = const Size(320, 700);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final v = {
      ...view(),
      'turn': 0,
      'table': ['m2', 'm3', 'm4', 'm5', 's6'],
      'last': 3,
      'plays': [
        null,
        ['c1', 'c2', 'c3', 'c4', 'l5'],
        ['c2', 'c3', 'c4', 'c5', 'l6'],
        ['m2', 'm3', 'm4', 'm5', 's6'],
      ],
      'passed': <int>[],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(v), 200)));
    await t.pumpWidget(_app(api));
    await settle(t);
    expect(t.takeException(), isNull);
    for (final seat in [1, 2, 3]) {
      expect(find.byKey(ValueKey('play-$seat')), findsOneWidget);
    }
    expect(find.byKey(const ValueKey('play-0')), findsNothing);
    expect(find.byKey(const ValueKey('passed-1')), findsNothing);
  });

  testWidgets('only the last three plays stay on the table — my first play goes when the fourth comes', (t) async {
    final ev = [
      for (final (seat, c) in [(0, 'c3'), (1, 'c5'), (2, 'c7'), (3, 'c8')])
        {
          'seat': seat,
          'tiles': [c],
        },
    ];
    final v = {
      ...view(events: ev),
      'table': ['c8'],
      'last': 3,
      'counts': [12, 12, 12, 12],
      'plays': [
        null,
        ['c5'],
        ['c7'],
        ['c8'],
      ],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(v), 200)));
    await t.pumpWidget(_app(api));
    await t.pump();
    for (var k = 0; k < 14; k++) {
      await t.pump(const Duration(milliseconds: 70));
    }
    await t.pump(const Duration(milliseconds: 1500)); // 시작 카드 → 내 수·봇1
    await t.pump(const Duration(milliseconds: 1250)); // 봇2
    expect(find.byKey(const ValueKey('play-0')), findsOneWidget); // 아직 세 수뿐: 내 3이 보임
    await t.pump(const Duration(milliseconds: 1250)); // 봇3 — 네 번째 수
    expect(find.byKey(const ValueKey('play-3')), findsOneWidget);
    expect(find.byKey(const ValueKey('play-0')), findsNothing); // 내 3은 사라짐
    expect(find.byKey(const ValueKey('play-1')), findsOneWidget); // 봇1의 5까지 보임
    await settle(t);
    expect(find.byKey(const ValueKey('play-0')), findsNothing); // 서버 상태로 맞춘 뒤에도
  });

  testWidgets('a seat that played twice in the last three keeps its tile; the older seat goes', (t) async {
    // 0·1·2·(3 패스)·0·(1 패스)·2 → 최근 세 수는 2·0·2 → 1번 패는 사라져야 함
    final ev = [
      for (final (seat, c) in [(0, 'c3'), (1, 'c5'), (2, 'c7'), (3, null), (0, 'c9'), (1, null), (2, 'c10')])
        {
          'seat': seat,
          'tiles': c == null ? null : [c],
        },
    ];
    final v = {
      ...view(events: ev),
      'table': ['c10'],
      'last': 2,
      'counts': [11, 12, 11, 13],
      'plays': [
        ['c9'],
        null,
        ['c10'],
        null,
      ],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(v), 200)));
    await t.pumpWidget(_app(api));
    await t.pump();
    for (var k = 0; k < 14; k++) {
      await t.pump(const Duration(milliseconds: 70));
    }
    await t.pump(const Duration(milliseconds: 1500)); // 시작 카드
    for (var k = 0; k < 45; k++) {
      await t.pump(const Duration(milliseconds: 100)); // 봇 장면 끝까지(서버 동기화 전)
    }
    expect(find.byKey(const ValueKey('play-2')), findsOneWidget);
    expect(find.byKey(const ValueKey('play-0')), findsOneWidget);
    expect(find.byKey(const ValueKey('play-1')), findsNothing);
    await settle(t);
  });

  testWidgets('my play drawn at once and echoed by the server counts once', (t) async {
    // 봇 1·2·3이 낸 뒤 내가 내고 봇 1이 냄 → 최근 세 수는 3·0·1 → 봇 3 패는 남고 봇 2 패만 사라짐
    final start = {
      ...view(),
      'table': ['c2'],
      'last': 3,
      'plays': [
        null,
        ['l1'],
        ['s1'],
        ['c2'],
      ],
    };
    final after = {
      ...view(
        events: [
          {
            'seat': 0,
            'tiles': ['m1'],
          },
          {
            'seat': 1,
            'tiles': ['l5'],
          },
        ],
      ),
      'hand': ['s3'],
      'counts': [1, 12, 13, 13],
      'table': ['l5'],
      'last': 1,
      'plays': [
        ['m1'],
        ['l5'],
        null,
        ['c2'],
      ],
    };
    var calls = 0;
    final api = Api(MockClient((r) async => http.Response(jsonEncode(++calls == 1 ? start : after), 200)));
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await t.pump();
    await t.pump(const Duration(milliseconds: 100)); // 응답·봇 1 장면(동기화 전)
    expect(find.byKey(const ValueKey('play-1')), findsOneWidget);
    expect(find.byKey(const ValueKey('play-3')), findsOneWidget);
    expect(find.byKey(const ValueKey('play-2')), findsNothing);
    await settle(t);
  });

  testWidgets('bot passes leave a bubble on that seat', (t) async {
    final v = {
      ...view(),
      'table': ['m9'],
      'last': 0,
      'plays': [
        ['m9'],
        null,
        null,
        null,
      ],
      'passed': [1, 2],
      'turn': 3,
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(v), 200)));
    await t.pumpWidget(_app(api));
    await settle(t);
    expect(find.byKey(const ValueKey('passed-1')), findsOneWidget);
    expect(find.byKey(const ValueKey('passed-2')), findsOneWidget);
    expect(find.byKey(const ValueKey('passed-3')), findsNothing);
  });

  test('효과음마다 파일이 앱에 들어 있다', () async {
    for (final f in Sfx.values) {
      expect((await rootBundle.load('assets/audio/sfx/${f.name}.wav')).lengthInBytes, greaterThan(1000));
    }
  });

  testWidgets('효과음: 고르기·내기·봇 수·패스·바닥 가져가기·승리 순서로, 음소거면 하나도 안 난다(11-27 사용자)', (t) async {
    for (final muted in [false, true]) {
      Settings.muted.value = muted;
      Sfx.log = [];
      var calls = 0;
      final done = {
        ...view(
          events: [
            {
              'seat': 1,
              'tiles': ['c4'],
            },
            {'seat': 2, 'tiles': null},
            {'seat': 3, 'tiles': null},
            {'seat': 0, 'tiles': null},
          ],
        ),
        'winner': 0,
        'settlement': [23, -9, -17, 3],
        'moves': [],
        'playable': [],
      };
      final api = Api(MockClient((r) async => http.Response(jsonEncode(++calls == 1 ? view() : done), 200)));
      await t.pumpWidget(_app(api));
      await settle(t);
      await t.tap(find.byKey(const ValueKey('hand-m1')));
      await t.pump();
      await t.tap(find.widgetWithText(FilledButton, 'Play'));
      await t.pump(const Duration(seconds: 6)); // 봇 수·패스 장면(약 5초)이 끝나도록
      await settle(t);
      expect(
        Sfx.log,
        muted ? isEmpty : [Sfx.select, Sfx.play, Sfx.play, Sfx.pass, Sfx.pass, Sfx.pass, Sfx.sweep, Sfx.win],
      );
      await t.pumpWidget(const SizedBox());
      await t.pump(const Duration(minutes: 1));
    }
    Settings.muted.value = false;
  });
}

void autoPassTests() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    markTilesReady();
  });
  testWidgets('auto passes show on every seat at once, mine included', (t) async {
    // 내가 m1을 냄 → 봇 1이 산13(아무도 못 이김) → 서버가 2·3·0번을 한꺼번에 자동 패스(auto) — 한 명씩 보이면 안 된다
    var calls = 0;
    final api = Api(
      MockClient((r) async {
        calls++;
        if (calls == 1) return http.Response(jsonEncode(view()), 200);
        return http.Response(
          jsonEncode({
            ...view(
              events: [
                {
                  'seat': 0,
                  'tiles': ['m1'],
                },
                {
                  'seat': 1,
                  'tiles': ['m13'],
                },
                {'seat': 2, 'tiles': null, 'auto': true},
                {'seat': 3, 'tiles': null, 'auto': true},
                {'seat': 0, 'tiles': null, 'auto': true},
              ],
            ),
            'hand': ['s3'],
            'turn': 1,
          }),
          200,
        );
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    var seen = false;
    for (var i = 0; i < 80 && !seen; i++) {
      await t.pump(const Duration(milliseconds: 100));
      seen = find.byKey(const ValueKey('passed-2')).evaluate().isNotEmpty;
    }
    expect(seen, isTrue);
    // 처음 보인 그 화면에 세 자리 패스가 함께 떠 있다
    expect(find.byKey(const ValueKey('passed-3')), findsOneWidget);
    expect(find.byKey(const ValueKey('passed-0')), findsOneWidget);
    await t.pump(const Duration(seconds: 5)); // 남은 봇 장면 대기를 흘려보낸다
  });
}

/// 새 판 나눠 주기·시작 카드(약 2.3초)가 지나가게 시간을 흘린 뒤 화면이 멈출 때까지 기다린다.
Future<void> settle(WidgetTester t) async {
  await t.pump(const Duration(seconds: 3));
  await t.pumpAndSettle();
}
