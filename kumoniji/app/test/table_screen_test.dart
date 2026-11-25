import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/table_screen.dart';
import 'package:kumoniji/tile.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    markTilesReady();
  });
  moreTests();
  legalTests();
  recentTests();
  autoPassTests();
  testWidgets('pick a tile and play sends it', (t) async {
    final paths = <String>[];
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        paths.add(r.url.path);
        bodies.add(r.body.isEmpty ? null : jsonDecode(r.body));
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
        bodies.add(jsonDecode(r.body));
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
        bodies.add(r.body.isEmpty ? null : jsonDecode(r.body));
        return http.Response(jsonEncode({...view(), 'level': (bodies.last as Map?)?['level'] ?? 'normal'}), 200);
      }),
    );
    await t.pumpWidget(_app(api));
    await settle(t);
    expect(bodies, [
      {'level': 'normal'},
    ]); // 처음엔 중급
    expect(find.text('Kumoniji · Normal'), findsOneWidget);
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
    expect(find.text('Kumoniji · Hard'), findsOneWidget);
  });

  testWidgets('first request fails → retry button starts a game', (t) async {
    var calls = 0;
    final api = Api(
      MockClient((r) async => ++calls == 1 ? http.Response('', 503) : http.Response(jsonEncode(view()), 200)),
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
        bodies.add(jsonDecode(r.body));
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
        bodies.add(jsonDecode(r.body));
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
    testWidgets('a short ${size.width.toInt()}x${size.height.toInt()} window keeps the old hand size', (t) async {
      t.view.physicalSize = size;
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(_app(Api(MockClient((r) async => http.Response(jsonEncode(view()), 200)))));
      await settle(t);
      while (t.takeException() != null) {} // 낮은 가로 창의 옆자리 넘침은 이번 변경 전부터
      expect(t.getSize(find.byKey(ValueKey('hand-${view()['hand'][0]}'))).width, 56); // 키우지 않는다(옆자리 몫)
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
      // 예전 크기(최대 56)보다 작아지지 않는다 — 낮은 가로 화면은 한 줄로
      if (size.width > size.height) {
        expect(t.getSize(find.byKey(const ValueKey('hand-m1'))).width, greaterThanOrEqualTo(50));
      }
      // 실제로는 홈에서 들어와 왼쪽에 뒤로 가기(56)가 있다 — 배지가 그 자리를 남긴다
      expect(t.getRect(find.byKey(const ValueKey('today'))).left >= 56 + 8, isTrue);
    });
  }

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
