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
import 'package:kumoniji/wallet.dart';
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
      // 홈의 잔고 막대가 부르는 지갑은 이 테스트들의 관심 밖 — 401(로그아웃)이 아니라 없음으로 답한다
      final all = {'/api/wallet': (_) => http.Response('', 404), ...routes};
      return (all[r.url.path] ?? (_) => http.Response('{"detail":{"code":"session"}}', 401))(r);
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

  test('2단계 인증을 켠 직후 /me가 일시 장애여도 계정을 비우지 않고 복구 코드를 돌려준다(리뷰 39차)', () async {
    var meFails = true;
    fake({
      '/api/auth/mfa/enable': (_) => ok({
        'recovery_codes': ['a1', 'b2'],
      }),
      '/api/auth/me': (_) => meFails ? http.Response('', 503) : ok({'id': 1, 'email': 'me@x.com', 'nickname': 'me'}),
    });
    final before = Me.fromJson({'id': 1, 'email': 'me@x.com', 'nickname': 'me'});
    Auth.me.value = before;
    expect(await Auth.mfaEnable('123456'), ['a1', 'b2']);
    expect(Auth.me.value, same(before)); // 비우면 AuthGate가 복구 코드 대화상자를 걷는다
    meFails = false;
    await Future.delayed(const Duration(milliseconds: 1100)); // 뒤에서 다시 읽음(1초 뒤)
    expect(Auth.me.value, isNotNull);
    expect(Auth.me.value, isNot(same(before)));
  });

  test('설정을 바꾸기 전에 떠난 내 정보 읽기가 늦게 와도 바꾼 뒤의 읽기가 이긴다(리뷰 45차)', () async {
    final stale = Completer<http.Response>(), fresh = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path != '/api/auth/me') return http.Response('', 404);
        return ++n == 1 ? stale.future : fresh.future;
      }),
    );
    final before = Me.fromJson({'id': 1, 'nickname': 'me', 'mfa_enabled': true});
    Auth.me.value = before;
    final bg = Auth.reloadIfStill(before); // 뒤에서 세션 재확인 — MFA를 끄기 전에 떠남
    final after = Auth.reload(); // MFA를 끈 뒤 다시 읽기
    await Future<void>.delayed(Duration.zero);
    stale.complete(ok({'id': 1, 'nickname': 'me', 'mfa_enabled': true})); // 옛 상태가 먼저 도착
    await bg;
    fresh.complete(ok({'id': 1, 'nickname': 'me', 'mfa_enabled': false}));
    await after;
    expect(Auth.me.value?.mfaEnabled, isFalse);
  });

  test('설정을 바꾼 뒤의 읽기가 실패하면, 앞 읽기가 같은 세션의 옛 값을 넣었어도 다시 읽는다', () async {
    final stale = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path != '/api/auth/me') return http.Response('', 404);
        n++;
        if (n == 1) return stale.future;
        if (n <= 3) throw http.ClientException('offline'); // 바꾼 뒤의 읽기와 첫 재시도가 잠깐 실패
        return ok({'id': 1, 'nickname': 'me', 'mfa_enabled': true});
      }),
    );
    final before = Me.fromJson({'id': 1, 'nickname': 'me', 'mfa_enabled': false});
    Auth.me.value = before;
    final bg = Auth.reloadIfStill(before); // MFA를 켜기 전에 떠남
    final after = Auth.reload(); // MFA를 켠 뒤 다시 읽기
    await Future<void>.delayed(Duration.zero);
    stale.complete(ok({'id': 1, 'nickname': 'me', 'mfa_enabled': false})); // 옛 상태가 먼저 들어감
    await bg;
    await after;
    await Future<void>.delayed(const Duration(milliseconds: 1100)); // 1초 뒤 다시
    expect(Auth.me.value?.mfaEnabled, isTrue);
  });

  test('로그인 확인을 기다리는 사이 로그인·로그아웃했으면 늦은 응답이 홈을 다시 열지 않는다', () async {
    final slow = Completer<http.Response>();
    Auth.client = AuthClient(
      MockClient((r) async => r.url.path == '/api/auth/me' ? slow.future : http.Response('', 404)),
    );
    Auth.me.value = null;
    final load = Auth.load();
    await Future<void>.delayed(Duration.zero);
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'me'}); // 뒤의 복구가 먼저 홈을 엶
    Auth.me.value = null; // 로그아웃
    slow.complete(ok({'id': 1, 'nickname': 'me'})); // 옛 세션의 응답이 늦게
    await load;
    expect(Auth.me.value, isNull);
  });

  test('겹친 내 정보 읽기 중 앞 읽기가 다른 탭의 새 계정을 넣으면 늦은 옛 계정 읽기가 되돌리지 않는다(리뷰 46차)', () async {
    final first = Completer<http.Response>(), second = Completer<http.Response>();
    var n = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path != '/api/auth/me') return http.Response('', 404);
        return ++n == 1 ? first.future : second.future;
      }),
    );
    final a = Me.fromJson({'id': 1, 'nickname': 'a'});
    Auth.me.value = a;
    final bg = Auth.reloadIfStill(a);
    final later = Auth.reload();
    await Future<void>.delayed(Duration.zero);
    first.complete(ok({'id': 2, 'nickname': 'b'})); // 다른 탭이 B로 로그인한 뒤 도착
    await bg;
    second.complete(ok({'id': 1, 'nickname': 'a'})); // 옛 쿠키로 떠난 응답이 늦게
    await later;
    expect(Auth.me.value?.id, 2);
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

  testWidgets('session ends inside a pushed screen (missions) → back to the login screen, not hidden behind it', (
    t,
  ) async {
    var walletCalls = 0;
    fake({
      '/api/auth/config': (_) => ok({'google': false}),
      '/api/auth/me': (_) => walletCalls > 1 ? err(401, 'session') : ok(me), // 세션이 끝나면 /me도 401
      '/api/wallet': (_) => ++walletCalls == 1
          ? ok({
              'coins': 0,
              'gems': 0,
              'hearts': 10,
              'next_heart': null,
              'attend': {'day': '2026-11-26', 'streak': 0, 'claimed': false},
              'missions': {'all': [], 'done': [], 'counts': {}, 'bonus': false},
            })
          : err(401, 'session'),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('open-missions')));
    await settle(t);
    expect(find.byKey(const ValueKey('login')), findsOneWidget);
  });

  testWidgets('another tab switches the account (no logged-out frame) → pushed screens of the old account close', (
    t,
  ) async {
    fake({
      '/api/auth/config': (_) => ok({'google': false}),
      '/api/auth/me': (_) => ok(me),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('open-shop')));
    await settle(t);
    expect(find.byKey(const ValueKey('buy-hearts5')), findsOneWidget);
    Auth.me.value = Me.fromJson({...me, 'id': 2});
    await settle(t);
    expect(find.byKey(const ValueKey('buy-hearts5')), findsNothing);
    expect(find.text('Single player'), findsOneWidget);
  });

  testWidgets('another tab re-logs the same account into MFA-pending → wallet 403 mfa shows the code screen', (
    t,
  ) async {
    var pending = false;
    fake({
      '/api/auth/config': (_) => ok({'google': false}),
      '/api/auth/me': (_) => ok({...me, 'mfa_enabled': pending, 'mfa_passed': !pending}),
      '/api/wallet': (_) => pending ? http.Response('{"detail":{"code":"mfa"}}', 403) : http.Response('', 404),
    });
    await t.pumpWidget(_app(Uri.parse('https://k/')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('open-shop')));
    await settle(t);
    pending = true; // 다른 탭이 같은 계정으로 다시 로그인 — 2단계 인증 전
    Wallet.refresh();
    await settle(t);
    expect(find.byKey(const ValueKey('mfa-code')), findsOneWidget);
    expect(find.byKey(const ValueKey('buy-hearts5')), findsNothing);
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
        expect(jsonDecode(r.body)['refresh'], 'r1');
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
