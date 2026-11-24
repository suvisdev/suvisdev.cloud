import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/auth.dart';
import 'package:kumoniji/home_screen.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/main.dart';
import 'package:kumoniji/settings.dart';
import 'package:kumoniji/tile.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;
import 'table_screen_test.dart' show settle;

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
    markTilesReady();
    Settings.locale.value = null;
    Settings.vibration.value = true;
  });

  testWidgets('home has single, multi (disabled), how to play, options — no quit', (t) async {
    await t.pumpWidget(_home(Api(MockClient((_) async => http.Response('', 500)))));
    await settle(t);
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
    await settle(t);
    await t.tap(find.text('Single player'));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('level-hard')));
    for (var i = 0; i < 50 && find.text('Your turn').evaluate().isEmpty; i++) {
      await t.pump(const Duration(milliseconds: 100)); // 나눠 주기·시작 카드가 끝날 때까지
    }
    expect(bodies, [
      {'level': 'hard'},
    ]);
    expect(find.text('Your turn'), findsOneWidget);
    await t.tap(find.byType(BackButton));
    await settle(t);
    expect(find.text('Quit this game and leave?'), findsOneWidget);
    await t.tap(find.text('Cancel'));
    await settle(t);
    expect(find.text('Your turn'), findsOneWidget); // 그대로 남음
    await t.tap(find.byType(BackButton));
    await settle(t);
    await t.tap(find.text('Leave'));
    await settle(t);
    expect(find.text('Single player'), findsOneWidget); // 메인으로 돌아옴
  });

  testWidgets('options: language switches the whole app and is remembered; vibration and volume saved', (t) async {
    // 로그인된 계정으로 시작(쿠키·토큰이 살아 있는 상태)
    Auth.client = AuthClient(
      MockClient(
        (r) async => r.url.path == '/api/auth/me'
            ? http.Response(jsonEncode({'id': 1, 'email': 'me@x.com', 'nickname': 'me'}), 200)
            : http.Response('{}', 404),
      ),
    );
    await t.pumpWidget(const KumonijiApp());
    await settle(t);
    await t.tap(find.byIcon(Icons.settings));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('language')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('locale-ja')));
    await settle(t);
    expect(find.text('オプション'), findsOneWidget); // 화면이 바로 일본어로
    await t.tap(find.byKey(const ValueKey('vibration')));
    await settle(t);
    await t.drag(find.byKey(const ValueKey('music')), const Offset(-500, 0));
    await settle(t);
    final p = await SharedPreferences.getInstance();
    expect(p.getString('locale'), 'ja');
    expect(p.getBool('vibration'), false);
    expect(p.getDouble('music'), 0);
    await t.tap(find.byType(BackButton));
    await settle(t);
    expect(find.text('シングルモード'), findsOneWidget);
  });

  testWidgets('옵션에서 중국어(간체)를 고르면 화면이 바로 중국어로', (t) async {
    SharedPreferences.setMockInitialValues({});
    await Settings.load();
    Auth.client = AuthClient(
      MockClient(
        (r) async => r.url.path == '/api/auth/me'
            ? http.Response(jsonEncode({'id': 1, 'email': 'me@x.com', 'nickname': 'me'}), 200)
            : http.Response('{}', 404),
      ),
    );
    await t.pumpWidget(const KumonijiApp());
    await settle(t);
    await t.tap(find.byIcon(Icons.settings));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('language')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('locale-zh')));
    await settle(t);
    expect(find.text('设置'), findsOneWidget);
    expect((await SharedPreferences.getInstance()).getString('locale'), 'zh');
    await t.tap(find.byType(BackButton));
    await settle(t);
    expect(find.text('单人模式'), findsOneWidget);
    Settings.locale.value = null;
  });
}
