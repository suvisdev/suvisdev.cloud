import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
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

  group('앱 로그인 저장', () {
    Future<Map<String, dynamic>?> saved() async {
      await Auth.client.save(); // 차례로 쓰니 앞 저장이 다 끝난 뒤
      final s = await AuthClient.vault!.read(key: 'session');
      return s == null ? null : jsonDecode(s) as Map<String, dynamic>;
    }

    setUp(() => FlutterSecureStorage.setMockInitialValues({}));

    test('로그인하면 토큰·계정을 저장하고, 로그아웃하면 지운다', () async {
      fake({
        '/api/auth/login': (_) => ok({'verified': true, 'access': 'a1', 'refresh': 'r1'}),
        '/api/auth/me': (_) => ok(me),
        '/api/auth/logout': (_) => ok({}),
      });
      await Auth.login('me@x.com', 'pw');
      final first = await saved();
      // 재시도 키는 토큰을 받을 때 함께 저장 — 갱신 직전 쓰기는 안드로이드에서 디스크에 늦게 닿는다(리뷰 2차)
      expect(first, {'access': 'a1', 'refresh': 'r1', 'retry': isA<String>(), 'gen': isA<String>(), 'me': me});
      expect((await SharedPreferences.getInstance()).getString(AuthClient.genKey), first!['gen']);
      await Auth.logout();
      // 로그아웃이 끝났으면 저장소에서도 이미 지워졌다 — 곧바로 앱을 꺼도 옛 계정으로 켜지지 않게(리뷰 3차)
      expect(await AuthClient.vault!.read(key: 'session'), isNull);
    });

    test('다른 계정으로 로그인하는 사이 앞 계정이 화면에 들어와도 새 토큰 기록에 그 계정을 섞지 않는다(리뷰 20차)', () async {
      const b = {'id': 2, 'email': 'b@x.com', 'nickname': 'b', 'mfa_enabled': false, 'mfa_passed': true};
      final meB = Completer<http.Response>();
      Auth.client = AuthClient(
        MockClient(
          (r) async => switch (r.url.path) {
            '/api/auth/login' => ok({'verified': true, 'access': 'aB', 'refresh': 'rB'}),
            '/api/auth/me' => await meB.future,
            _ => http.Response('', 404),
          },
        ),
      );
      Auth.client.keep({'access': 'aA', 'refresh': 'rA'}); // 켤 때 되살린 A의 토큰
      Auth.me.value = Me.fromJson(me); // A의 늦은 다시 읽기가 로그인 화면 뒤에서 들어옴
      final login = Auth.login('b@x.com', 'pw'); // B로 로그인 — B의 /me는 아직
      await Future<void>.delayed(Duration.zero);
      final mid = await saved();
      expect(mid!['refresh'], 'rB');
      expect(mid['me'], isNull); // 여기서 앱이 꺼져도 B 토큰에 A의 닉네임·이메일이 붙지 않는다
      meB.complete(ok(b));
      await login;
      expect((await saved())!['me'], b);
    });

    test('비밀번호를 바꿔 새 토큰을 받아도 같은 계정이라 저장 기록의 계정은 그대로', () async {
      fake({
        '/api/auth/login': (_) => ok({'verified': true, 'access': 'a1', 'refresh': 'r1'}),
        '/api/auth/me': (_) => ok(me),
        '/api/auth/password': (_) => ok({'access': 'a2', 'refresh': 'r2'}),
      });
      await Auth.login('me@x.com', 'pw');
      await Auth.changePassword('new password 1');
      final after = await saved();
      expect(after!['refresh'], 'r2');
      expect(after['me'], me);
    });

    testWidgets('저장된 로그인이 있으면 서버 답을 기다리지 않고 첫 화면부터 홈, 세션이 끝났으면 로그인 화면으로', (t) async {
      SharedPreferences.setMockInitialValues({AuthClient.genKey: 'g1'});
      FlutterSecureStorage.setMockInitialValues({
        'session': jsonEncode({'access': 'a1', 'refresh': 'r1', 'retry': null, 'gen': 'g1', 'me': me}),
      });
      final answer = Completer<http.Response>();
      Auth.client = AuthClient(
        MockClient((r) => r.url.path == '/api/auth/me' ? answer.future : Future.value(err(401, 'session'))),
      );
      await t.runAsync(Auth.restore);
      await t.pumpWidget(_app(Uri.parse('https://x/')));
      await t.pump();
      expect(find.text('Single player'), findsOneWidget); // 답이 오기 전에 이미 홈
      answer.complete(err(401, 'session')); // 액세스 만료 + 갱신 거절 = 끝난 세션
      await t.runAsync(() => Future.delayed(const Duration(milliseconds: 50)));
      await settle(t);
      expect(find.text('Single player'), findsNothing);
      expect(Auth.me.value, isNull);
    });

    test('갱신을 보내기 전에 재시도 키를 저장 — 응답 뒤 저장 전에 꺼져도 다음 실행이 같은 키로 다시 받는다', () async {
      final keys = <String>[];
      var died = true;
      Auth.client = AuthClient(
        MockClient((r) async {
          if (r.url.path == '/api/auth/me') return ok(me);
          final b = jsonDecode(r.body) as Map;
          keys.add(b['retry'] as String);
          if (died) {
            // 서버는 회전했는데 앱이 새 토큰을 저장하기 전에 꺼짐: 지금 저장소 그대로 두고 응답을 잃는다
            died = false;
            throw http.ClientException('killed');
          }
          return ok({'access': 'a2', 'refresh': 'r2'});
        }),
      );
      Auth.client.keep({'access': 'a1', 'refresh': 'r1'});
      await Auth.client.save(); // 로그인 때 저장이 끝난 상태에서 시작
      await expectLater(Auth.client.refresh(), throwsA(isA<http.ClientException>()));
      // 다시 켬: 새 클라이언트가 저장소에서 읽는다
      Auth.client = AuthClient(Auth.client.inner);
      await Auth.restore();
      expect(await Auth.client.refresh(), isTrue);
      expect(keys, hasLength(2));
      expect(keys[1], keys[0]);
      expect((await saved())?['refresh'], 'r2');
    });

    test('보안 저장소에 키를 못 쓰면 옛 기록을 지우거나(못 지우면 세대를 지워) 무효로 한 뒤 갱신, 다음 실행에 되살아나지 않는다', () async {
      final real = AuthClient.vault;
      addTearDown(() => AuthClient.vault = real);
      FlutterSecureStorage.setMockInitialValues({
        'session': jsonEncode({'access': 'a1', 'refresh': 'r1', 'retry': null, 'me': me}),
      });
      var sentRefresh = 0;
      for (final deletable in [true, false]) {
        sentRefresh = 0;
        Auth.client = AuthClient(
          MockClient((r) async {
            sentRefresh++;
            return ok({'access': 'a2', 'refresh': 'r2'});
          }),
        );
        AuthClient.vault = real;
        Auth.client.keep({'access': 'a1', 'refresh': 'r1'});
        await Auth.client.save(); // r1과 그 키는 저장됨
        AuthClient.vault = _Broken(deletable: deletable);
        Auth.client.keep({'access': 'a1', 'refresh': 'r1b'}); // 그 뒤 받은 r1b는 못 씀 — 저장소엔 다른 토큰(r1)
        if (deletable) {
          expect(await Auth.client.refresh(), isTrue);
          expect(sentRefresh, 1);
          expect(await real!.read(key: 'session'), isNull); // 키 없는 옛 토큰은 남지 않는다
        } else {
          // 지우지 못해도 설정의 세대를 지워 남은 r1은 짝이 없다 — 갱신은 보내고, 새 토큰 저장 때 다시 적는 세대도 새것(리뷰 8차)
          expect(await Auth.client.refresh(), isTrue);
          expect(sentRefresh, 1);
          await Auth.client.save(); // 새 토큰 r2 저장 시도(설정엔 세대를 다시 적고, 저장소 쓰기는 실패)
          expect(await real!.read(key: 'session'), isNotNull); // r1 기록은 남아 있지만
          AuthClient.vault = real;
          Auth.client = AuthClient(Auth.client.inner);
          await Auth.restore();
          expect(Auth.client.hasTokens, isFalse); // 되살아나지 않는다
        }
      }
    });

    test('갱신 전 저장이 실패하는 사이 B가 로그인하면 A의 실패 처리가 B의 기록을 지우지 않는다', () async {
      final real = AuthClient.vault!;
      addTearDown(() => AuthClient.vault = real);
      FlutterSecureStorage.setMockInitialValues({});
      Auth.client = AuthClient(MockClient((r) async => ok({'access': 'a2', 'refresh': 'r2'})));
      Auth.client.keep({'access': 'a1', 'refresh': 'r1'});
      await Auth.client.save();
      final gate = Completer<void>();
      AuthClient.vault = _Gated(gate.future);
      final refreshing = Auth.client.refresh(); // A의 갱신: 보내기 전 저장이 문 앞에서 기다림
      await Future<void>.delayed(Duration.zero);
      Auth.client.keep({'access': 'b1', 'refresh': 'rB'}); // 그사이 B 로그인
      gate.complete();
      expect(await refreshing, isFalse);
      await Future<void>.delayed(const Duration(milliseconds: 20)); // 줄 선 B의 저장이 끝날 때까지(다시 저장하면 지운 걸 덮어 가린다)
      expect(jsonDecode((await real.read(key: 'session'))!)['refresh'], 'rB');
    });

    test('앞 계정 토큰이 남은 채 새로 로그인하고 그 저장이 실패해도, 다음 실행에 앞 계정이 되살아나지 않는다', () async {
      final real = AuthClient.vault;
      addTearDown(() => AuthClient.vault = real);
      FlutterSecureStorage.setMockInitialValues({});
      Auth.client.keep({'access': 'a1', 'refresh': 'rA'}); // A 로그인(/me는 실패해 로그인 화면에 머묾)
      await Auth.client.save();
      AuthClient.vault = const _Broken(deletable: false);
      Auth.client.keep({'access': 'b1', 'refresh': 'rB'}); // B 로그인 — 저장소 쓰기 실패
      await Auth.client.save();
      AuthClient.vault = real;
      Auth.client = AuthClient(Auth.client.inner); // 다음 실행
      await Auth.restore();
      expect(Auth.client.hasTokens, isFalse);
    });

    test('저장소가 처음부터 고장 나 아무것도 못 썼으면 갱신은 그대로 보낸다(남은 옛 토큰이 없으니 안전)', () async {
      final real = AuthClient.vault;
      addTearDown(() => AuthClient.vault = real);
      AuthClient.vault = const _Broken(deletable: false);
      var sentRefresh = 0;
      Auth.client = AuthClient(
        MockClient((r) async {
          sentRefresh++;
          return ok({'access': 'a2', 'refresh': 'r2'});
        }),
      );
      Auth.client.keep({'access': 'a1', 'refresh': 'r1'});
      expect(await Auth.client.refresh(), isTrue);
      expect(await Auth.client.refresh(), isTrue); // 다음 만료 때도
      expect(sentRefresh, 2);
    });

    test('로그아웃 때 저장소를 못 지워도, 새 로그인을 못 저장해도 옛 로그인은 되살아나지 않는다(로그인 세대)', () async {
      final real = AuthClient.vault;
      addTearDown(() => AuthClient.vault = real);
      fake({
        '/api/auth/login': (_) => ok({'verified': true, 'access': 'a1', 'refresh': 'r1'}),
        '/api/auth/me': (_) => ok(me),
        '/api/auth/logout': (_) => ok({}),
      });
      Future<void> relaunch() async {
        AuthClient.vault = real; // 다시 켬: 저장소는 살아났고, 못 지운 옛 기록이 그대로(앞 클라이언트는 더 저장하지 않음)
        Auth.client = AuthClient(Auth.client.inner);
        await Auth.restore();
      }

      // ① 로그아웃했는데 저장소 지우기가 실패
      await Auth.login('me@x.com', 'pw');
      await Auth.client.save();
      AuthClient.vault = const _Broken(deletable: false);
      await Auth.logout();
      expect(await real!.read(key: 'session'), isNotNull);
      await relaunch();
      expect(Auth.client.hasTokens, isFalse);
      expect(await real.read(key: 'session'), isNull); // 짝 없는 기록은 지운다

      // ② A가 저장된 채(켤 때 못 읽어 로그인 화면) B로 로그인했는데 B 저장은 실패
      await Auth.login('me@x.com', 'pw');
      await Auth.client.save();
      Auth.client = AuthClient(Auth.client.inner); // 켤 때 저장소를 못 읽어 빈 손으로 시작
      AuthClient.vault = const _Broken(deletable: false);
      await Auth.login('b@x.com', 'pw');
      await Auth.client.save();
      await relaunch();
      expect(Auth.client.hasTokens, isFalse); // A 기록은 세대가 달라 버린다

      // ③ 정상 로그인은 다음 실행에 되살아난다
      await Auth.login('me@x.com', 'pw');
      await Auth.client.save();
      await relaunch();
      expect(Auth.client.hasTokens, isTrue);
    });

    test('첫 실행에 옛 기록을 못 지워도, 그 실행에서 저장한 로그인은 다음 실행에 되살아난다', () async {
      final real = AuthClient.vault;
      addTearDown(() => AuthClient.vault = real);
      FlutterSecureStorage.setMockInitialValues({
        'session': jsonEncode({'access': 'a0', 'refresh': 'r0', 'gen': 'old', 'me': me}), // 지웠다 깐 앱의 키체인 잔여
      });
      fake({
        '/api/auth/login': (_) => ok({'verified': true, 'access': 'a1', 'refresh': 'r1'}),
        '/api/auth/me': (_) => ok(me),
      });
      AuthClient.vault = const _Broken(deletable: false);
      await Auth.restore(); // 첫 실행: 세대 없음 → 안 살림, 지우기는 실패
      expect(Auth.client.hasTokens, isFalse);
      AuthClient.vault = real; // 저장소가 살아남
      await Auth.login('me@x.com', 'pw');
      await Auth.client.save();
      Auth.client = AuthClient(Auth.client.inner); // 다음 실행
      await Auth.restore();
      expect(Auth.client.hasTokens, isTrue);
    });

    test('앱을 지웠다 다시 설치하면(설정과 함께 세대가 지워짐) 키체인에 남은 옛 로그인을 버린다', () async {
      SharedPreferences.setMockInitialValues({});
      FlutterSecureStorage.setMockInitialValues({
        'session': jsonEncode({'access': 'a1', 'refresh': 'r1', 'me': me}),
      });
      fake({});
      await Auth.restore();
      expect(Auth.me.value, isNull);
      expect(Auth.client.hasTokens, isFalse);
      expect(await AuthClient.vault!.read(key: 'session'), isNull);
    });
  });

  test('메일 인증 전 계정은 비밀번호가 맞아도 마지막 로그인 이메일로 적지 않는다', () async {
    final p = await SharedPreferences.getInstance();
    await p.setString(Auth.lastEmailKey, 'a@x.com');
    fake({
      '/api/auth/login': (_) => ok({'verified': false}),
    });
    await Auth.login('b@x.com', 'pw');
    await Future<void>.delayed(const Duration(milliseconds: 20));
    expect(p.getString(Auth.lastEmailKey), 'a@x.com');
  });

  testWidgets('로그인한 이메일은 이 기기에 기억해 다음 로그인 화면에 채우고, 탈퇴하면 지운다', (t) async {
    fake({
      '/api/auth/login': (_) => ok({'verified': true, 'access': 'a1', 'refresh': 'r1'}),
      '/api/auth/me': (_) => ok(me),
      '/api/auth/delete': (_) => ok({}),
    });
    await t.runAsync(() => Auth.login(' me@x.com ', 'pw'));
    await t.runAsync(() => Future.delayed(const Duration(milliseconds: 20)));
    expect((await SharedPreferences.getInstance()).getString(Auth.lastEmailKey), 'me@x.com');
    Auth.client.keep(null); // 로그아웃한 뒤 다시 켬
    Auth.me.value = null;
    fake({});
    await t.pumpWidget(_app(Uri.parse('https://x/')));
    await settle(t);
    expect(find.descendant(of: find.byKey(const ValueKey('email')), matching: find.text('me@x.com')), findsOneWidget);
    fake({'/api/auth/delete': (_) => ok({})});
    await t.runAsync(() async {
      Auth.me.value = Me.fromJson(me); // 저장(save)도 진짜 비동기 안에서 — 가짜 시계 안에서 시작한 쓰기는 끝나지 않는다
      await Auth.deleteAccount();
    });
    await t.runAsync(() => Future.delayed(const Duration(milliseconds: 20)));
    expect((await SharedPreferences.getInstance()).getString(Auth.lastEmailKey), isNull);
  });

  testWidgets('홈의 프로필 버튼 → 계정 화면에서 닉네임을 바꾸고, 구글로만 가입한 계정은 메일로 비밀번호를 만든다', (t) async {
    var nick = 'me';
    final sent = fake({
      '/api/auth/me': (_) => ok({
        ...me,
        'nickname': nick,
        'has_password': false,
        'providers': ['google'],
      }),
      '/api/auth/nickname': (r) {
        nick = jsonDecode(r.body)['nickname'];
        return ok({'nickname': nick});
      },
      '/api/auth/reset/request': (_) => ok({}),
      '/api/auth/mfa/setup': (_) => err(403, 'reauth'),
    });
    await t.pumpWidget(_app(Uri.parse('https://x/')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('open-profile')));
    await settle(t);
    expect(find.text('Change password'), findsNothing); // 비밀번호가 없으니 바꾸기 대신 만들기
    await t.tap(find.text('Change nickname'));
    await settle(t);
    await t.enterText(find.byKey(const ValueKey('ask')), 'newname');
    await t.tap(find.text('Confirm'));
    await settle(t);
    await t.runAsync(() => Future.delayed(const Duration(milliseconds: 20)));
    await settle(t);
    expect(Auth.me.value?.nickname, 'newname');
    expect(find.text('newname'), findsOneWidget);
    await t.tap(find.text('Set a password (by email)'));
    await settle(t);
    await t.runAsync(() => Future.delayed(const Duration(milliseconds: 20)));
    final reset = sent.lastWhere((r) => r.url.path == '/api/auth/reset/request');
    expect(jsonDecode(reset.body), {'email': 'me@x.com'});
    // 비밀번호 없는 계정이 본인 확인이 필요한 일을 하면 멈추지 않고 비밀번호부터 만들라고 안내(리뷰 4차)
    await settle(t);
    await t.tap(find.text('Turn on two-step verification'));
    await settle(t);
    await t.runAsync(() => Future.delayed(const Duration(milliseconds: 20)));
    await t.pump();
    expect(find.textContaining('or use "Set a password (by email)" first'), findsOneWidget);
  });

  testWidgets('로그인을 기다리는 사이 키보드로 다시 제출해도 로그인 요청은 하나', (t) async {
    final answer = Completer<http.Response>();
    var logins = 0;
    Auth.client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/login') {
          logins++;
          return answer.future;
        }
        return err(401, 'session');
      }),
    );
    await t.pumpWidget(_app(Uri.parse('https://x/')));
    await settle(t);
    await t.enterText(find.byKey(const ValueKey('email')), 'me@x.com');
    await t.enterText(find.byKey(const ValueKey('password')), 'pw');
    await t.testTextInput.receiveAction(TextInputAction.done);
    await t.pump();
    await t.showKeyboard(find.byKey(const ValueKey('password'))); // 제출하면 키보드가 닫힌다 — 다시 열고
    await t.testTextInput.receiveAction(TextInputAction.done); // 응답 전 두 번째 제출
    await t.pump();
    expect(logins, 1);
    answer.complete(err(401, 'credentials'));
    await settle(t);
  });

  testWidgets('앱 로그인 화면: 서버가 구글 클라이언트 ID를 주면 구글 버튼이 보이고, 없으면 안 보인다', (t) async {
    const cid = 'web-client.apps.googleusercontent.com';
    for (final (id, os, shown) in [
      (cid, TargetPlatform.android, true),
      ('', TargetPlatform.android, false),
      (cid, TargetPlatform.iOS, false), // iOS 클라이언트는 아직 없음
    ]) {
      debugDefaultTargetPlatformOverride = os;
      fake({
        '/api/auth/config': (_) => ok({'google': true, 'turnstile_site': '', 'google_client': id}),
      });
      await t.pumpWidget(const SizedBox());
      await t.pumpWidget(_app(Uri.parse('https://x/')));
      await settle(t);
      final found = find.byKey(const ValueKey('google')).evaluate().length;
      debugDefaultTargetPlatformOverride = null;
      expect(found, shown ? 1 : 0, reason: '$id $os');
    }
  });

  test('보이는 계정이 바뀌면(뒤의 복구로 들어와도) 마지막 로그인 이메일도 그 계정 것, 이메일 없으면 지움', () async {
    final p = await SharedPreferences.getInstance();
    await p.setString(Auth.lastEmailKey, 'before@x.com');
    Auth.me.value = Me.fromJson({...me, 'email': 'b@x.com'});
    await Future<void>.delayed(Duration.zero);
    expect(p.getString(Auth.lastEmailKey), 'b@x.com');
    Auth.me.value = Me.fromJson({...me, 'id': 2, 'email': null});
    await Future<void>.delayed(Duration.zero);
    expect(p.getString(Auth.lastEmailKey), isNull);
    Auth.me.value = null;
  });

  test('구글이 준 ID 토큰과 nonce를 서버(/google/app)에 보내 로그인한다', () async {
    final sent = fake({
      '/api/auth/google/app': (_) => ok({'access': 'a1', 'refresh': 'r1'}),
      '/api/auth/me': (_) => ok(me),
    });
    await (await SharedPreferences.getInstance()).setString(Auth.lastEmailKey, 'before@x.com'); // 앞사람
    await Auth.googleApp('id-token', 'nonce-1234567890');
    await Future<void>.delayed(Duration.zero);
    expect((await SharedPreferences.getInstance()).getString(Auth.lastEmailKey), me['email'], reason: '앞사람 이메일이 남지 않음');
    final post = sent.firstWhere((r) => r.url.path == '/api/auth/google/app');
    expect(jsonDecode(post.body), {'id_token': 'id-token', 'nonce': 'nonce-1234567890'});
    expect(post.headers['x-kumoniji-client'], 'app');
    expect(Auth.me.value?.id, 1);
  });

  test('앱을 막 켜 토큰이 없으면 서버에 묻지 않고 바로 로그인 전으로(시작 왕복 아끼기)', () async {
    Auth.skipMeWithoutTokens = true;
    addTearDown(() => Auth.skipMeWithoutTokens = false);
    var calls = 0;
    Auth.client = AuthClient(
      MockClient((_) async {
        calls++;
        return http.Response(jsonEncode({'id': 1, 'nickname': 'a'}), 200);
      }),
    );
    expect(await Auth.load(), isNull);
    expect(calls, 0);
    Auth.client.keep({'access': 'a', 'refresh': 'r'}); // 로그인해 토큰이 생기면 묻는다
    expect((await Auth.load())?.id, 1);
    expect(calls, 1);
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
    expect(find.byKey(const ValueKey('buy-coins1000')), findsOneWidget);
    Auth.me.value = Me.fromJson({...me, 'id': 2});
    await settle(t);
    expect(find.byKey(const ValueKey('buy-coins1000')), findsNothing);
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
    expect(find.byKey(const ValueKey('buy-coins1000')), findsNothing);
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

/// 쓰기는 늘 실패하는 보안 저장소. [deletable]이면 지우기는 진짜 저장소(목)에.
/// 첫 쓰기는 문이 열릴 때까지 기다렸다 실패, 그다음부터는 진짜 저장소
class _Gated extends FlutterSecureStorage {
  _Gated(this.gate);
  final Future<void> gate;
  var _first = true;

  @override
  Future<void> write({
    required String key,
    required String? value,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (_first) {
      _first = false;
      await gate;
      throw Exception('keystore');
    }
    await const FlutterSecureStorage().write(key: key, value: value);
  }

  @override
  Future<void> delete({
    required String key,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) => const FlutterSecureStorage().delete(key: key);
}

class _Broken extends FlutterSecureStorage {
  final bool deletable;
  const _Broken({required this.deletable});

  @override
  Future<void> write({
    required String key,
    required String? value,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) => Future.error(Exception('keystore'));

  @override
  Future<void> delete({
    required String key,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) => deletable ? const FlutterSecureStorage().delete(key: key) : Future.error(Exception('keystore'));
}
