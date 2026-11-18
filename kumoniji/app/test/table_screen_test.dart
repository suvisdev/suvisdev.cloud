import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/table_screen.dart';

import 'api_test.dart' show view;

void main() {
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
    await t.pumpAndSettle();
    expect(find.text('Your turn'), findsOneWidget);
    // 바닥이 비었으니 패스는 막혀 있다
    expect(t.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Pass')).onPressed, isNull);
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await t.pumpAndSettle();
    expect(paths, ['/api/games', '/api/games/a/moves']);
    expect(bodies.last, {
      'tiles': ['m1'],
    });
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
  testWidgets('first request fails → retry button starts a game', (t) async {
    var calls = 0;
    final api = Api(
      MockClient((r) async => ++calls == 1 ? http.Response('', 503) : http.Response(jsonEncode(view()), 200)),
    );
    await t.pumpWidget(_app(api));
    await t.pumpAndSettle();
    await t.tap(find.widgetWithText(FilledButton, 'New game'));
    await t.pumpAndSettle();
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
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('hand-m1')));
    await t.pump();
    await t.tap(find.widgetWithText(FilledButton, 'Play'));
    await t.pumpAndSettle();
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
    await t.pumpAndSettle();
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
    await t.pumpAndSettle();
    final names = t.widgetList<ListTile>(find.byType(ListTile)).map((e) => (e.title as Text).data).toList();
    expect(names, ['Bot 3', 'Bot 2', 'You', 'Bot 1']);
  });
}

void recentTests() {
  testWidgets('5-tile previous play fits a 320px-wide phone without overflow', (t) async {
    t.view.physicalSize = const Size(320, 700);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final v = {
      ...view(),
      'turn': 1,
      'table': ['m2', 'm3', 'm4', 'm5', 's6'],
      'last': 3,
      'recent': [
        {
          'seat': 1,
          'tiles': ['c1', 'c2', 'c3', 'c4', 'l5'],
        },
        {
          'seat': 2,
          'tiles': ['c2', 'c3', 'c4', 'c5', 'l6'],
        },
      ],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(v), 200)));
    await t.pumpWidget(_app(api));
    await t.pumpAndSettle();
    expect(t.takeException(), isNull);
    expect(find.text('Bot 1'), findsWidgets);
  });
}
