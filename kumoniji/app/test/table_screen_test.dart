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
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));
  moreTests();
  legalTests();
  recentTests();
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
    // 바닥이 비었으니 패스는 막혀 있다
    expect(t.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Pass')).onPressed, isNull);
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
    await t.pump(const Duration(milliseconds: 100));
    expect(find.byKey(const ValueKey('start-card')), findsOneWidget); // 시작 카드
    expect(find.text('×13'), findsNWidgets(3)); // 봇이 내기 전 13장씩
    expect(find.byKey(const ValueKey('play-3')), findsNothing); // 아직 아무도 안 냄
    await t.pump(const Duration(milliseconds: 1600));
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
}

void recentTests() {
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

/// 새 판 시작 카드(1.6초)가 지나가게 시간을 흘린 뒤 화면이 멈출 때까지 기다린다.
Future<void> settle(WidgetTester t) async {
  await t.pump(const Duration(seconds: 2));
  await t.pumpAndSettle();
}
