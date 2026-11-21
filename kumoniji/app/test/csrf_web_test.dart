@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/auth.dart';

void main() {
  test('another tab replaced the CSRF cookie (403 csrf) → fetch the current value and retry once', () async {
    var cookie = 'old';
    final seen = <String?>[];
    final client = AuthClient(
      MockClient((r) async {
        if (r.url.path == '/api/auth/csrf') return http.Response('{"csrf":"$cookie"}', 200);
        seen.add(r.headers['x-csrf']);
        return r.headers['x-csrf'] == cookie
            ? http.Response('{}', 200)
            : http.Response('{"detail":{"code":"csrf"}}', 403);
      }),
    );
    expect((await client.post(Uri.parse('/api/auth/signup'))).statusCode, 200); // 'old'를 기억
    cookie = 'new'; // 다른 탭이 덮어씀
    expect((await client.post(Uri.parse('/api/auth/login'))).statusCode, 200); // 로그인도 복구
    expect(seen, ['old', 'old', 'new']);
  });
}
