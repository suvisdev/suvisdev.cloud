import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show ValueNotifier, kIsWeb;
import 'package:http/http.dart' as http;

import 'api.dart' show Api;

/// 로그인한 계정(서버 /api/auth/me).
class Me {
  final int id;
  final String? email;
  final String nickname;
  final bool mfaEnabled, mfaPassed, hasPassword;
  final List<String> providers;

  Me.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      email = j['email'],
      nickname = j['nickname'] ?? '',
      mfaEnabled = j['mfa_enabled'] ?? false,
      mfaPassed = j['mfa_passed'] ?? true,
      hasPassword = j['has_password'] ?? false,
      providers = List<String>.from(j['providers'] ?? const []);

  /// MFA가 켜져 있는데 아직 이 세션에서 통과하지 않음 → 코드 화면.
  bool get needsMfa => mfaEnabled && !mfaPassed;
  bool get hasGoogle => providers.contains('google');
}

/// 서버가 거절한 이유. code는 서버의 detail.code(credentials·wait·captcha·password_short …).
class AuthError implements Exception {
  final int status;
  final String? code;
  final int seconds;
  const AuthError(this.status, [this.code, this.seconds = 0]);
}

/// 모든 요청이 거치는 클라이언트(게임 API 포함).
/// - 웹: 같은 원점이라 브라우저가 __Host- 쿠키를 붙인다. 상태를 바꾸는 요청에는 CSRF 값을 X-CSRF 머리글로 보낸다.
/// - 앱: X-Kumoniji-Client: app + Bearer. ponytail: 토큰은 메모리에만 — 앱 출시 전에 Keystore 보관으로 바꿔야 자동 로그인이 된다.
/// 401이면 리프레시로 한 번 갱신한 뒤 다시 보낸다(동시에 여러 요청이 401이어도 갱신은 한 번).
class AuthClient extends http.BaseClient {
  final http.Client inner;
  String? _csrf, _access, _refresh;
  Future<String>? _csrfFetch;
  Future<bool>? _refreshing;
  Duration raceWait = const Duration(seconds: 1);
  AuthClient([http.Client? inner]) : inner = inner ?? http.Client();

  static const _noRetry = {'/api/auth/refresh', '/api/auth/login', '/api/auth/csrf', '/api/auth/me'};

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final first = await _send(request as http.Request);
    final status = first.statusCode;
    if (status != 401 && status != 403) return first;
    final bytes = await first.stream.toBytes();
    final again = http.StreamedResponse(Stream.value(bytes), status, headers: first.headers, request: first.request);
    final code = _code(bytes);
    // 403 csrf(로그인 포함 — 비밀번호 확인 전에 거절되니 실패가 쌓이지 않는다): 다른 탭이 CSRF 쿠키를 새로 받아 덮어씀 — 이 탭이 기억한 값을 버리고 지금 쿠키 값으로 한 번 더
    if (status == 403) {
      if (code != 'csrf' || !kIsWeb) return again;
      _csrf = null;
      _csrfFetch = null;
      return _send(_copy(request));
    }
    // 세션이 끝난 401(code: session)만 갱신한다. 틀린 MFA 코드·비밀번호(credentials)를 다시 보내면 실패가 두 번 쌓인다.
    if (code != 'session' || _noRetry.contains(request.url.path) || !await refresh()) return again;
    return _send(_copy(request));
  }

  static String? _code(List<int> body) {
    try {
      final j = jsonDecode(utf8.decode(body));
      final d = j is Map ? j['detail'] ?? j : null;
      return d is Map ? d['code'] as String? : null;
    } catch (_) {
      return null;
    }
  }

  Future<http.StreamedResponse> _send(http.Request r) async {
    if (kIsWeb) {
      // 동시에 여러 요청이 시작돼도 CSRF 값은 한 번만 받는다(따로 받으면 쿠키가 덮여 나머지가 403)
      if (r.method != 'GET') r.headers['x-csrf'] = _csrf ??= await _getCsrf();
    } else {
      r.headers['x-kumoniji-client'] = 'app';
      if (_access != null) r.headers['authorization'] = 'Bearer $_access';
    }
    return inner.send(r);
  }

  http.Request _copy(http.Request r) => http.Request(r.method, r.url)
    ..headers.addAll(r.headers)
    ..bodyBytes = r.bodyBytes;

  /// 실패하면 다음 요청에서 다시 받는다(실패한 Future를 계속 재사용하면 새로고침 전까지 모든 요청이 막힌다).
  Future<String> _getCsrf() => _csrfFetch ??= _fetchCsrf().catchError((Object e) {
    _csrfFetch = null;
    throw e;
  });

  Future<String> _fetchCsrf() async {
    final r = await inner.get(Uri.parse('${Api.base}/api/auth/csrf'));
    if (r.statusCode != 200) throw http.ClientException('csrf ${r.statusCode}');
    return jsonDecode(r.body)['csrf'] as String;
  }

  /// 리프레시 토큰으로 새 액세스(회전). 실패하면 로그아웃 상태.
  Future<bool> refresh() => _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);

  Future<bool> _doRefresh() async {
    if (!kIsWeb && _refresh == null) return false;
    final r = await _send(
      http.Request('POST', Uri.parse('${Api.base}/api/auth/refresh'))
        ..headers['content-type'] = 'application/json'
        ..body = kIsWeb ? '{}' : jsonEncode({'refresh': _refresh}),
    );
    final body = await r.stream.bytesToString();
    // 409: 다른 탭이 방금 같은 쿠키를 갱신함 — 그 탭의 응답이 새 쿠키를 심을 때까지 잠깐 기다린 뒤 공유 쿠키로 다시 시도
    if (r.statusCode == 409) {
      await Future.delayed(raceWait);
      return true;
    }
    if (r.statusCode != 200) {
      keep(null);
      return false;
    }
    keep(jsonDecode(body));
    return true;
  }

  /// 앱: 응답 본문의 토큰을 기억(웹은 쿠키라 할 일 없음). null이면 잊는다.
  void keep(Map<String, dynamic>? body) {
    if (kIsWeb) return;
    _access = body?['access'] ?? (body == null ? null : _access);
    _refresh = body?['refresh'] ?? (body == null ? null : _refresh);
  }
}

/// 계정 API. 화면은 이 함수들만 부른다.
class Auth {
  static AuthClient client = AuthClient(); // 테스트는 가짜 서버로 바꾼다
  static final me = ValueNotifier<Me?>(null);

  static Uri _uri(String path) => Uri.parse('${Api.base}/api/auth$path');

  static Future<Map<String, dynamic>> _post(String path, [Map<String, dynamic>? body]) async {
    final r = await client.post(
      _uri(path),
      headers: {'content-type': 'application/json'},
      body: jsonEncode(body ?? {}),
    );
    return _decode(r);
  }

  static Map<String, dynamic> _decode(http.Response r) {
    final text = utf8.decode(r.bodyBytes);
    final j = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
    if (r.statusCode >= 300) {
      final d = j is Map ? j['detail'] ?? j : null;
      throw AuthError(r.statusCode, d is Map ? d['code'] as String? : null, d is Map ? (d['seconds'] ?? 0) as int : 0);
    }
    return j is Map<String, dynamic> ? j : {'items': j};
  }

  /// 시작할 때: 쿠키(웹)나 기억한 토큰으로 로그인돼 있는지. 액세스가 만료됐으면 리프레시를 한 번 해 본다.
  static Future<Me?> load() async {
    try {
      var r = await client.get(_uri('/me'));
      if (r.statusCode == 401 && await client.refresh()) r = await client.get(_uri('/me'));
      me.value = r.statusCode == 200 ? Me.fromJson(_decode(r)) : null;
    } on AuthError {
      me.value = null;
    }
    return me.value;
  }

  static Future<Map<String, dynamic>> config() async => _decode(await client.get(_uri('/config')));

  /// 반환: verified(false면 메일 인증 전), mfa_required.
  static Future<Map<String, dynamic>> login(String email, String password, {String? captcha}) async {
    final j = await _post('/login', {'email': email, 'password': password, 'captcha': captcha});
    client.keep(j);
    if (j['verified'] == true) await load();
    return j;
  }

  static Future<void> signup(String email, String password, String nickname) =>
      _post('/signup', {'email': email, 'password': password, 'nickname': nickname});
  static Future<void> resend(String email) => _post('/resend', {'email': email});
  static Future<void> forgot(String email) => _post('/reset/request', {'email': email});

  /// 메일 링크: kind는 verify·reset·email·protect.
  static Future<bool> linkValid(String kind, String token) async {
    final path = {'verify': '/verify/check', 'reset': '/reset/check', 'protect': '/protect/check'}[kind];
    if (path == null) return true; // 주소 확인은 미리 보는 API가 없다 — 누르면 서버가 판단
    try {
      return (_decode(await client.get(_uri('$path?token=${Uri.encodeQueryComponent(token)}'))))['valid'] == true;
    } on AuthError {
      return false;
    }
  }

  static Future<void> useLink(String kind, String token, {String? password}) => switch (kind) {
    'verify' => _post('/verify', {'token': token, 'password': password}),
    'reset' => _post('/reset', {'token': token, 'password': password}),
    'email' => _post('/email/confirm', {'token': token}),
    _ => _post('/protect', {'token': token}),
  };

  static Future<void> mfaVerify(String code) async {
    await _post('/mfa/verify', {'code': code});
    await load();
  }

  static Future<void> logout({bool everywhere = false}) async {
    try {
      await _post(everywhere ? '/logout-all' : '/logout');
    } on AuthError {
      // 이미 만료된 세션 — 어차피 로그아웃 상태
    }
    client.keep(null);
    me.value = null;
  }

  static Future<void> reauth(String password) => _post('/reauth', {'password': password});

  static Future<void> changePassword(String password) async =>
      client.keep(await _post('/password', {'password': password}));
  static Future<void> changeEmail(String email) => _post('/email', {'email': email});
  static Future<Map<String, dynamic>> mfaSetup() => _post('/mfa/setup');

  static Future<List<String>> mfaEnable(String code) async {
    final j = await _post('/mfa/enable', {'code': code});
    await load();
    return List<String>.from(j['recovery_codes']);
  }

  static Future<void> mfaDisable(String code) async {
    await _post('/mfa/disable', {'code': code});
    await load();
  }

  static Future<List<String>> newRecoveryCodes() async =>
      List<String>.from((await _post('/mfa/recovery'))['recovery_codes']);

  static Future<void> unlinkGoogle() async {
    await _post('/google/unlink');
    await load();
  }

  static Future<void> deleteAccount() async {
    await _post('/delete');
    client.keep(null);
    me.value = null;
  }

  /// 웹에서 구글로 보낼 주소(서버가 PKCE·state·nonce를 만든다).
  static String googleStart({bool link = false, bool reauth = false}) =>
      '${Api.base}/api/auth/google/start${link
          ? '?link=true'
          : reauth
          ? '?reauth=true'
          : ''}';
}
