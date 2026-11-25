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
    Settings.muted.value = false;
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
    await t.pump();
    expect(bodies, isEmpty); // 고르기만 해서는 시작하지 않는다
    await t.tap(find.byKey(const ValueKey('level-start')));
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

  testWidgets('level dialog scrolls on a short landscape screen', (t) async {
    t.view.physicalSize = const Size(640, 300);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(jsonDecode(r.body));
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await t.pumpWidget(_home(api));
    await settle(t);
    await t.ensureVisible(find.text('Single player')); // 낮은 화면이라 홈도 스크롤된다
    await t.pump();
    await t.tap(find.text('Single player'));
    await settle(t);
    expect(t.takeException(), isNull); // 넘침 없음
    await t.dragUntilVisible(
      find.byKey(const ValueKey('level-hard')),
      find.byType(SingleChildScrollView).last,
      const Offset(0, -50),
    );
    await t.tap(find.byKey(const ValueKey('level-hard')));
    await t.pump();
    final old = FlutterError.onError;
    FlutterError.onError = (_) {}; // 판 화면은 높이 300에서 원래부터 넘친다(범위 밖) — 여기서는 난이도 창만 본다
    await t.tap(find.byKey(const ValueKey('level-start')));
    await t.pump();
    expect(bodies, [
      {'level': 'hard'},
    ]);
    for (var i = 0; i < 50; i++) {
      await t.pump(const Duration(milliseconds: 100)); // 나눠 주기 애니메이션 타이머를 끝낸다
    }
    FlutterError.onError = old;
  });

  testWidgets('finished game result Home goes back to the home screen', (t) async {
    final done = {
      ...view(),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(done), 200)));
    await t.pumpWidget(_home(api));
    await settle(t);
    await t.tap(find.text('Single player'));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('level-start')));
    for (var i = 0; i < 50 && find.byKey(const ValueKey('result-home')).evaluate().isEmpty; i++) {
      await t.pump(const Duration(milliseconds: 100));
    }
    await t.tap(find.byKey(const ValueKey('result-home')));
    await settle(t);
    expect(find.text('Single player'), findsOneWidget);
    expect(find.byKey(const ValueKey('result-home')), findsNothing);
  });

  testWidgets('four suit tiles shrink together in a 280px window', (t) async {
    t.view.physicalSize = const Size(280, 700);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(_home(Api(MockClient((r) async => http.Response('{}', 200)))));
    await settle(t);
    expect(t.takeException(), isNull);
    expect(t.getRect(find.byWidgetPredicate((w) => w is TileView && w.code == 'c13')).right <= 280, isTrue);
  });

  testWidgets('home shows one tile of each suit and one mute button silences music and effects', (t) async {
    await t.pumpWidget(_home(Api(MockClient((r) async => http.Response('{}', 200)))));
    await settle(t);
    for (final c in ['m13', 's13', 'l12', 'c13']) {
      expect(find.byWidgetPredicate((w) => w is TileView && w.code == c), findsOneWidget);
    }
    Settings.music.value = 0.6;
    Settings.sfx.value = 0.8;
    await t.tap(find.byKey(const ValueKey('mute')));
    await t.pump();
    expect((Settings.musicVolume, Settings.sfxVolume), (0.0, 0.0));
    expect(find.byIcon(Icons.volume_off), findsOneWidget);
    expect((await SharedPreferences.getInstance()).getBool('muted'), true);
    await t.tap(find.byKey(const ValueKey('mute')));
    await t.pump();
    expect((Settings.musicVolume, Settings.sfxVolume), (0.6, 0.8)); // 음량 값은 그대로 돌아온다
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
