import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/account_screen.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/auth.dart';
import 'package:kumoniji/auth_screens.dart';
import 'package:kumoniji/help.dart';
import 'package:kumoniji/home_screen.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/level.dart';
import 'package:kumoniji/settings.dart';
import 'package:kumoniji/table_screen.dart';
import 'package:kumoniji/tile.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;
import 'auth_test.dart' show fake, ok, me;
import 'table_screen_test.dart' show settle;

/// 앱은 가로가 기본(11-25 사용자) — 휴대폰 가로 크기에서 화면마다 넘침이 없는지 본다.
const sizes = [Size(740, 360), Size(844, 390), Size(915, 412), Size(400, 300)];

Widget _wrap(Widget home, {String lang = 'en'}) => MaterialApp(
  locale: Locale(lang),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: home,
);

final hand = ['m1', 'm4', 's3', 's5', 'l2', 'l7', 'c3', 'c6', 'm9', 's10', 'l11', 'c12', 'm13'];
Map<String, dynamic> game({bool done = false, bool practice = true}) => {
  ...view(),
  'hand': hand,
  'counts': [13, 13, 13, 13],
  'playable': done ? [] : hand,
  'moves': done
      ? []
      : [
          for (final h in hand) [h],
        ],
  'out': ?(practice ? <String>[] : null),
  if (done) 'winner': 3,
  if (done) 'settlement': [-9, -17, 3, 23],
};

Future<List<String>> overflows(WidgetTester t, Size size, Future<void> Function() body) async {
  t.view.physicalSize = size;
  t.view.devicePixelRatio = 1;
  addTearDown(t.view.reset);
  final old = FlutterError.onError;
  final errors = <String>[];
  FlutterError.onError = (e) => errors.add(e.exceptionAsString().split('\n').first);
  try {
    await body();
  } finally {
    FlutterError.onError = old;
  }
  return errors;
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    markTilesReady();
    Settings.locale.value = null;
    Auth.me.value = null;
  });

  testWidgets('a portrait window keeps the stacked layout (not the low landscape one)', (t) async {
    await overflows(t, const Size(320, 550), () async {
      await t.pumpWidget(_wrap(TableScreen(api: Api(MockClient((_) async => http.Response(jsonEncode(game()), 200))))));
      await settle(t);
    });
    final suit = t.getRect(find.byKey(const ValueKey('suit-order')));
    expect(suit.top >= kToolbarHeight, isTrue, reason: '$suit'); // 위 막대가 아니라 본문에
  });

  testWidgets('account input dialog scrolls above the keyboard on a 360px-high phone', (t) async {
    final e = await overflows(t, const Size(740, 360), () async {
      fake({});
      Auth.me.value = Me.fromJson({...me, 'has_password': true});
      await t.pumpWidget(_wrap(const AccountScreen()));
      await settle(t);
      await t.scrollUntilVisible(find.text('Change email'), 100);
      await t.tap(find.text('Change email'));
      t.view.viewInsets = const FakeViewPadding(bottom: 200); // 입력란에 포커스 → 키보드
      addTearDown(t.view.resetViewInsets);
      await settle(t);
    });
    expect(e, isEmpty);
    expect(find.byKey(const ValueKey('ask')).hitTestable(), findsOneWidget);
  });

  testWidgets('account input field fits fully above a 220px keyboard on a 320px-high phone', (t) async {
    final e = await overflows(t, const Size(700, 320), () async {
      fake({});
      Auth.me.value = Me.fromJson({...me, 'has_password': true});
      await t.pumpWidget(_wrap(const AccountScreen()));
      await settle(t);
      await t.scrollUntilVisible(find.text('Change email'), 100);
      await t.tap(find.text('Change email'));
      t.view.viewInsets = const FakeViewPadding(bottom: 220);
      addTearDown(t.view.resetViewInsets);
      await settle(t);
      await t.ensureVisible(find.byKey(const ValueKey('ask')));
      await settle(t);
    });
    expect(e, isEmpty);
    final r = t.getRect(find.byKey(const ValueKey('ask')));
    expect(r.top >= 0 && r.bottom <= 100, isTrue, reason: '$r'); // 키보드 위 100px 안에 입력란 전체
  });

  for (final lang in ['en', 'ko', 'ja', 'zh']) {
    testWidgets('pass bubble on the one-line opposite seat leaves ×1 readable ($lang)', (t) async {
      final v = {
        ...game(),
        'counts': [13, 13, 1, 13],
        'table': ['m9'],
        'last': 0,
        'plays': [
          ['m9'],
          null,
          null,
          null,
        ],
        'passed': [2],
        'turn': 3,
      };
      await overflows(t, const Size(740, 360), () async {
        await t.pumpWidget(
          _wrap(TableScreen(api: Api(MockClient((_) async => http.Response(jsonEncode(v), 200)))), lang: lang),
        );
        await settle(t);
      });
      final bubble = t.getRect(find.byKey(const ValueKey('passed-2')));
      final count = t.getRect(find.text('×1'));
      expect(bubble.overlaps(count), isFalse, reason: '$bubble / $count');
    });
  }

  for (final size in sizes) {
    final name = '${size.width.toInt()}x${size.height.toInt()}';
    for (final lang in ['en', 'ko']) {
      testWidgets('home $name $lang', (t) async {
        final e = await overflows(t, size, () async {
          await t.pumpWidget(
            _wrap(
              HomeScreen(api: Api(MockClient((_) async => http.Response('', 500))), showHelpOnFirstVisit: false),
              lang: lang,
            ),
          );
          await settle(t);
        });
        expect(e, isEmpty);
      });
    }
    testWidgets('table 13 tiles $name', (t) async {
      final e = await overflows(t, size, () async {
        await t.pumpWidget(
          _wrap(TableScreen(api: Api(MockClient((_) async => http.Response(jsonEncode(game()), 200))))),
        );
        await settle(t);
      });
      expect(e, isEmpty);
    });
    testWidgets('only-pass hint at 200% text keeps pass on screen $name', (t) async {
      t.platformDispatcher.textScaleFactorTestValue = 2;
      addTearDown(t.platformDispatcher.clearTextScaleFactorTestValue);
      final v = {
        ...game(),
        'table': ['c13'],
        'last': 3,
        'playable': <String>[],
        'moves': <List<String>>[],
      };
      final e = await overflows(t, size, () async {
        await t.pumpWidget(_wrap(TableScreen(api: Api(MockClient((_) async => http.Response(jsonEncode(v), 200))))));
        await settle(t);
      });
      expect(e, isEmpty); // 안내문이 줄바꿈으로 길어져도 판(남은 장수·낸 패)이 넘치지 않는다(리뷰 9차)
      final pass = t.getRect(find.widgetWithText(OutlinedButton, 'Pass'));
      expect(pass.bottom <= size.height && pass.right <= size.width, isTrue, reason: '$pass');
      expect({for (final c in hand) t.getRect(find.byKey(ValueKey('hand-$c'))).top}.length, 1);
    });
    testWidgets('table multi $name', (t) async {
      final e = await overflows(t, size, () async {
        await t.pumpWidget(
          _wrap(TableScreen(api: Api(MockClient((_) async => http.Response(jsonEncode(game(practice: false)), 200))))),
        );
        await settle(t);
      });
      expect(e, isEmpty);
    });
    testWidgets('result $name', (t) async {
      final e = await overflows(t, size, () async {
        await t.pumpWidget(
          _wrap(TableScreen(api: Api(MockClient((_) async => http.Response(jsonEncode(game(done: true)), 200))))),
        );
        await settle(t);
      });
      expect(e, isEmpty);
    });
    testWidgets('help and level $name', (t) async {
      final e = await overflows(t, size, () async {
        await t.pumpWidget(
          _wrap(
            Builder(
              builder: (c) => Scaffold(
                body: Column(
                  children: [
                    TextButton(onPressed: () => showHelp(c), child: const Text('help')),
                    TextButton(
                      onPressed: () => pickLevel(c, current: 'normal'),
                      child: const Text('level'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
        await t.tap(find.text('help'));
        await settle(t);
        Navigator.of(t.element(find.byType(Scaffold).first)).pop();
        await settle(t);
        await t.tap(find.text('level'));
        await settle(t);
      });
      expect(e, isEmpty);
    });
    testWidgets('login and account $name', (t) async {
      final e = await overflows(t, size, () async {
        fake({
          '/api/auth/config': (_) => ok({'google': true, 'turnstile_site': ''}),
        });
        await t.pumpWidget(_wrap(AuthGate(start: Uri.parse('https://k/'))));
        await settle(t);
        Auth.me.value = Me.fromJson(me);
        await t.pumpWidget(_wrap(const AccountScreen()));
        await settle(t);
      });
      expect(e, isEmpty);
    });
  }
}
