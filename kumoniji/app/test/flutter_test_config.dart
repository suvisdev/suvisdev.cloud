import 'dart:async';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kumoniji/auth.dart';
import 'package:kumoniji/practice.dart';
import 'package:kumoniji/sfx.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 테스트의 가짜 서버는 웹처럼 토큰 없이(쿠키로) /me가 통한다 — 앱의 '토큰 없으면 묻지 않기'는 끄고, 그 동작은 따로 시험한다
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  Auth.skipMeWithoutTokens = false;
  FlutterSecureStorage.setMockInitialValues({}); // 로그인 저장은 메모리 가짜 저장소로
  // 로그인 세대(Auth 저장)도 설정에 — 테스트마다 새로: 앞 테스트(가짜 시계)에서 만든 설정 인스턴스를 기다리면 끝나지 않는다
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    AuthClient.forgetPrefsGen();
    // 앞 테스트의 클라이언트는 버린다 — 그 저장 줄(가짜 시계에서 시작해 끝나지 않은 쓰기)에 이번 테스트의 저장이 걸리지 않게
    Auth.client = AuthClient();
    // 폰 화면의 떠 있는 창은 닫힌 채로 시작
    PracticeFrame.floatOut.value = false;
    PracticeFrame.floatCombos.value = false;
    // 넓은 화면 옆 패널: 나온 패는 처음엔 숨김(11-28 사용자), 조합표는 보임
    PracticeFrame.showOut.value = false;
    PracticeFrame.showCombos.value = true;
    Sfx.log = []; // 효과음은 이름만 쌓는다(재생기 플러그인이 없다)
  });
  await testMain();
}
