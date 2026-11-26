import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/auth.dart';
import 'package:kumoniji/auth_screens.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/settings.dart';
import 'package:kumoniji/tile.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'table_screen_test.dart' show settle;

const me = {'id': 1, 'email': 'me@x.com', 'nickname': 'me', 'mfa_enabled': false, 'mfa_passed': true};

Widget _app(Uri start) => MaterialApp(
  locale: const Locale('en'),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: AuthGate(start: start),
);

/// 가짜 서버: 경로 → 응답. 받은 요청은 sent에 쌓는다.
List<http.Request> fake(Map<String, http.Response Function(http.Request)> routes) {
  final sent = <http.Request>[];
  Auth.client = AuthClient(
    MockClient((r) async {
      sent.add(r);
      return (routes[r.url.path] ?? (_) => http.Response('{"detail":{"code":"session"}}', 401))(r);
    }),
  );
  return sent;
}

http.Response ok(Object body) => http.Response(jsonEncode(body), 200);
http.Response err(int status, String code) => http.Response(
  jsonEncode({
    'detail': {'code': code},
  }),
  status,
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    markTilesReady();
    Auth.me.value = null;
  });

  testWidgets('not logged in → login screen; wrong password shows the reason', (t) async {
    fake({
      '/api/auth/config': (_) => ok({'google': false, 'turnstile_site': ''}),
      '/api/auth/login': (_) => err(401, 'credentials'),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/')));
    await settle(t);
    expect(find.byKey(const ValueKey('login')), findsOneWidget);
    await t.enterText(find.byKey(const ValueKey('email')), 'me@x.com');
    await t.enterText(find.byKey(const ValueKey('password')), 'nope');
    await t.tap(find.byKey(const ValueKey('login')));
    await settle(t);
    expect(find.text('Wrong email or password.'), findsOneWidget);
  });

  testWidgets('config is fetched together with /me at start, and the login screen does not fetch it again', (t) async {
    final meDone = Completer<http.Response>();
    final sent = <String>[];
    Auth.client = AuthClient(
      MockClient((r) async {
        sent.add(r.url.path);
        if (r.url.path == '/api/auth/me') return meDone.future;
        if (r.url.path == '/api/auth/config') return ok({'google': false});
        return err(401, 'session');
      }),
    );
    await t.pumpWidget(_app(Uri.parse('https://k/')));
    await t.pump();
    expect(sent, contains('/api/auth/config')); // /me 응답 전에 이미(11-26 시작 속도)
    meDone.complete(err(401, 'session'));
    await settle(t);
    expect(find.byKey(const ValueKey('login')), findsOneWidget);
    expect(sent.where((p) => p == '/api/auth/config').length, 1);
  });

  test('prefetch is dropped when already logged in, so the login screen after logout fetches fresh', () async {
    var key = '';
    Auth.client = AuthClient(
      MockClient(
        (r) async => r.url.path == '/api/auth/me'
            ? ok({'id': 1, 'email': 'a@x.com', 'nickname': 'n'})
            : ok({'google': false, 'turnstile': key}),
      ),
    );
    Auth.prefetchConfig();
    await Auth.load(); // 로그인돼 있음 — 로그인 화면을 거치지 않는다
    key = 'site-key'; // 그사이 서버가 캡차를 켜고, 사용자가 로그아웃
    expect((await Auth.config())['turnstile'], 'site-key');
  });

  test('a failed prefetch is not reused once the network is back', () async {
    var down = true;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (down) throw http.ClientException('offline');
        return ok({'google': true});
      }),
    );
    Auth.prefetchConfig();
    await Future<void>.delayed(Duration.zero);
    down = false;
    expect((await Auth.config())['google'], true);
  });

  test('a prefetch still in flight that fails is retried for the login screen', () async {
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (++calls == 1) throw http.ClientException('offline'); // 시작 때만 끊김
        return ok({'google': true});
      }),
    );
    Auth.prefetchConfig();
    expect((await Auth.config())['google'], true); // 진행 중인 미리 받기를 가져가 실패 → 새로
  });

  test('prefetched config is used once; the next login screen fetches fresh settings', () async {
    var key = '';
    Auth.client = AuthClient(MockClient((r) async => ok({'google': false, 'turnstile': key})));
    Auth.prefetchConfig();
    expect((await Auth.config())['turnstile'], '');
    key = 'site-key'; // 그사이 서버가 캡차를 켰다
    expect((await Auth.config())['turnstile'], 'site-key');
  });

  testWidgets('successful login goes to the home screen (stays logged in via /me)', (t) async {
    var loggedIn = false;
    fake({
      '/api/auth/config': (_) => ok({'google': false}),
      '/api/auth/login': (_) {
        loggedIn = true;
        return ok({'verified': true, 'mfa_required': false, 'access': 'a', 'refresh': 'r'});
      },
      '/api/auth/me': (_) => loggedIn ? ok(me) : err(401, 'session'),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/')));
    await settle(t);
    await t.enterText(find.byKey(const ValueKey('email')), 'me@x.com');
    await t.enterText(find.byKey(const ValueKey('password')), 'correct horse battery');
    await t.tap(find.byKey(const ValueKey('login')));
    await settle(t);
    expect(find.text('Single player'), findsOneWidget);
  });

  testWidgets('MFA-pending session shows the code screen first', (t) async {
    fake({
      '/api/auth/me': (_) => ok({...me, 'mfa_enabled': true, 'mfa_passed': false}),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/')));
    await settle(t);
    expect(find.byKey(const ValueKey('mfa-code')), findsOneWidget);
    expect(find.text('Single player'), findsNothing);
  });

  testWidgets('verify link: opening it only checks; pressing confirm sends token + new password', (t) async {
    final sent = fake({
      '/api/auth/verify/check': (_) => ok({'valid': true}),
      '/api/auth/verify': (_) => ok({'status': 'verified'}),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/verify?token=tok123')));
    await settle(t);
    expect(sent.every((r) => r.method == 'GET'), isTrue); // 여는 것만으로는 토큰을 쓰지 않는다
    expect(sent.map((r) => r.url.path), contains('/api/auth/verify/check'));
    expect(sent.map((r) => r.url.path), isNot(contains('/api/auth/config'))); // 링크 화면에선 미리 받지 않는다(리뷰 3차)
    await t.enterText(find.byKey(const ValueKey('link-pw')), 'correct horse battery');
    await t.tap(find.byKey(const ValueKey('link-go')));
    await settle(t);
    final post = sent.firstWhere((r) => r.url.path == '/api/auth/verify');
    expect(jsonDecode(post.body), {'token': 'tok123', 'password': 'correct horse battery'});
    expect(find.text('Verified. Please log in.'), findsOneWidget);
  });

  testWidgets('the /forgot link from the "already registered" mail opens password reset', (t) async {
    fake({
      '/api/auth/config': (_) => ok({'google': false}),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/forgot')));
    await settle(t);
    expect(find.text('Forgot password?'), findsOneWidget); // 찾기 화면 제목
    expect(find.byKey(const ValueKey('login')), findsNothing);
  });

  testWidgets('used or expired link says so', (t) async {
    fake({
      '/api/auth/reset/check': (_) => ok({'valid': false}),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/reset?token=old')));
    await settle(t);
    expect(find.text('This link has expired or was already used.'), findsOneWidget);
    expect(find.byKey(const ValueKey('link-go')), findsNothing);
  });

  test('401 refreshes once, then retries with the new access token', () async {
    var refreshes = 0;
    final sent = fake({
      '/api/auth/login': (_) => ok({'verified': false, 'access': 'old', 'refresh': 'r1'}),
      '/api/auth/refresh': (r) {
        refreshes++;
        expect(jsonDecode(r.body), {'refresh': 'r1'});
        return ok({'access': 'new', 'refresh': 'r2'});
      },
      '/api/games': (r) => r.headers['authorization'] == 'Bearer new' ? ok({}) : err(401, 'session'),
    });
    await Auth.login('me@x.com', 'pw');
    final r = await Auth.client.post(Uri.parse('/api/games'));
    expect(r.statusCode, 200);
    expect(refreshes, 1);
    expect(sent.where((r) => r.url.path == '/api/games').length, 2);
  });

  test('another tab already refreshed (409) → retry with the shared cookie, no logout', () async {
    var games = 0;
    fake({
      '/api/auth/login': (_) => ok({'verified': false, 'access': 'old', 'refresh': 'r1'}),
      '/api/auth/refresh': (_) => http.Response('{"code":"rotated"}', 409),
      '/api/games': (_) => ++games == 1 ? err(401, 'session') : ok({}),
    });
    Auth.client.raceWait = Duration.zero;
    await Auth.login('me@x.com', 'pw');
    expect((await Auth.client.post(Uri.parse('/api/games'))).statusCode, 200);
    expect(games, 2);
  });

  test('wrong MFA code (401 credentials) is sent once — no refresh, no second failure', () async {
    var refreshes = 0;
    final sent = fake({
      '/api/auth/refresh': (_) {
        refreshes++;
        return ok({'access': 'a', 'refresh': 'r'});
      },
      '/api/auth/mfa/verify': (_) => err(401, 'credentials'),
      '/api/auth/login': (_) => ok({'verified': false, 'access': 'a0', 'refresh': 'r0'}),
    });
    await Auth.login('me@x.com', 'pw'); // 리프레시 토큰을 가진 상태
    await expectLater(Auth.mfaVerify('000000'), throwsA(isA<AuthError>().having((e) => e.code, 'code', 'credentials')));
    expect(sent.where((r) => r.url.path == '/api/auth/mfa/verify').length, 1);
    expect(refreshes, 0);
  });

  test('failed refresh means logged out (no retry loop)', () async {
    fake({'/api/auth/refresh': (_) => err(401, 'session')});
    final r = await Auth.client.post(Uri.parse('/api/games'));
    expect(r.statusCode, 401);
  });

  test('화면 언어를 Accept-Language로 보낸다(메일 언어) — 고른 언어, 없으면 기기 언어', () async {
    final seen = <String?>[];
    final c = AuthClient(
      MockClient((r) async {
        seen.add(r.headers['accept-language']);
        return http.Response('{}', 200);
      }),
    );
    await c.get(Uri.parse('http://x/api/auth/me'));
    Settings.locale.value = const Locale('zh');
    await c.get(Uri.parse('http://x/api/auth/me'));
    Settings.locale.value = null;
    expect(seen, [Settings.lang, 'zh']);
    Settings.locale.value = const Locale('ja');
    expect(Auth.googleStart(link: true), endsWith('/api/auth/google/start?lang=ja&link=true'));
    Settings.locale.value = null;
  });

  test('기기 언어가 프랑스어·중국어 순이면 메일 언어도 화면처럼 중국어', () {
    expect(Settings.langFor(const [Locale('fr'), Locale('zh')]), 'zh');
    expect(Settings.langFor(const [Locale('fr')]), 'en'); // 지원 언어가 없으면 첫 지원 언어(en)
  });
}
