import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/home_screen.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/main.dart';
import 'package:kumoniji/settings.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;

Widget _home(Api api) => MaterialApp(
  locale: const Locale('en'),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: HomeScreen(api: api, showHelpOnFirstVisit: false),
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Settings.locale.value = null;
    Settings.vibration.value = true;
  });

  testWidgets('home has single, multi (disabled), how to play, options — no quit', (t) async {
    await t.pumpWidget(_home(Api(MockClient((_) async => http.Response('', 500)))));
    await t.pumpAndSettle();
    expect(find.text('Single player'), findsOneWidget);
    final multi = find.ancestor(of: find.text('Multiplayer · Coming soon'), matching: find.byType(OutlinedButton));
    expect(t.widget<OutlinedButton>(multi).onPressed, isNull);
    expect(find.text('How to play'), findsOneWidget);
    expect(find.text('Options'), findsOneWidget);
  });

  testWidgets('single → pick level → game; back mid-game asks before leaving', (t) async {
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(jsonDecode(r.body));
        return http.Response(jsonEncode({...view(), 'level': 'hard'}), 200);
      }),
    );
    await t.pumpWidget(_home(api));
    await t.pumpAndSettle();
    await t.tap(find.text('Single player'));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('level-hard')));
    await t.pumpAndSettle();
    expect(bodies, [
      {'level': 'hard'},
    ]);
    expect(find.text('Your turn'), findsOneWidget);
    await t.tap(find.byType(BackButton));
    await t.pumpAndSettle();
    expect(find.text('Quit this game and leave?'), findsOneWidget);
    await t.tap(find.text('Cancel'));
    await t.pumpAndSettle();
    expect(find.text('Your turn'), findsOneWidget); // 그대로 남음
    await t.tap(find.byType(BackButton));
    await t.pumpAndSettle();
    await t.tap(find.text('Leave'));
    await t.pumpAndSettle();
    expect(find.text('Single player'), findsOneWidget); // 메인으로 돌아옴
  });

  testWidgets('options: language switches the whole app and is remembered; vibration and volume saved', (t) async {
    await t.pumpWidget(const KumonijiApp());
    await t.pumpAndSettle();
    await t.tap(find.byIcon(Icons.settings));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('language')));
    await t.pumpAndSettle();
    await t.tap(find.byKey(const ValueKey('locale-ja')));
    await t.pumpAndSettle();
    expect(find.text('オプション'), findsOneWidget); // 화면이 바로 일본어로
    await t.tap(find.byKey(const ValueKey('vibration')));
    await t.pumpAndSettle();
    await t.drag(find.byKey(const ValueKey('music')), const Offset(-500, 0));
    await t.pumpAndSettle();
    final p = await SharedPreferences.getInstance();
    expect(p.getString('locale'), 'ja');
    expect(p.getBool('vibration'), false);
    expect(p.getDouble('music'), 0);
    await t.tap(find.byType(BackButton));
    await t.pumpAndSettle();
    expect(find.text('シングルモード'), findsOneWidget);
  });
}
