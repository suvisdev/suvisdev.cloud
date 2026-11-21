import 'package:flutter/widgets.dart';

void goTo(String url) {}

/// 메일 링크의 토큰이 주소창·방문 기록에 남지 않게 지운다.
void cleanUrl() {}

/// 사람 확인 위젯. 앱에는 없다 — 서버가 요구하면 웹에서 로그인하라고 안내한다.
Widget turnstile(String siteKey, ValueChanged<String> onToken) => const SizedBox.shrink();
const hasTurnstile = false;
