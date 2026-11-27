import 'dart:async';
import 'dart:convert';
import 'dart:math' show Random;

import 'package:flutter/foundation.dart' show ValueNotifier, kIsWeb;
import 'package:http/http.dart' as http;

import 'api.dart' show Api, GuardedRequest;
import 'settings.dart' show Settings;

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

  /// 서버로 나가는 모든 요청(CSRF·갱신 포함)의 응답 제한 — 멈춘 응답을 연결 실패(예외)로 끝내 다시 시도 경로로 보낸다.
  /// 여기 한 곳에 건다: 같이 쓰는 CSRF·갱신이 멈추면 위에서 건 제한으로는 풀리지 않고, 늦게 온 갱신 응답이
  /// 그사이 로그인한 다른 계정의 토큰을 덮는다(리뷰 18~23차)
  Duration timeout = const Duration(seconds: 15);
  AuthClient([http.Client? inner]) : inner = inner ?? http.Client();

  static const _anyAccount = {'/api/auth/me', '/api/auth/refresh', '/api/auth/csrf'};
  static const _noRetry = {'/api/auth/refresh', '/api/auth/login', '/api/auth/csrf', '/api/auth/me'};

  /// 마지막 응답(CSRF·세션 갱신 뒤 다시 보낸 것 포함)이 409 account_changed면 — 다른 탭에서 다른 계정으로 로그인함
  /// (쿠키는 탭끼리 같이 씀) — 이 탭의 계정을 버리고 지금 쿠키의 계정을 다시 읽는다(리뷰 5·7차).
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // 이 화면의 계정을 요청을 시작한 순간에 고정 — CSRF를 기다리거나 다시 보내는 사이 바뀐 계정을 붙이지 않게(리뷰 6·8차).
    // 서버가 세션 계정과 다르면 409 account_changed로 거절한다(지갑·하트를 다른 계정에서 안 쓰게)
    // 내 정보 다시 읽기·갱신에는 안 붙인다 — /me는 바뀐 계정을 읽어 와야 한다. 로그아웃에는 붙인다: 안 붙이면
    // 다른 탭에서 로그인한 B의 세션을 A 화면이 폐기한다. 계정이 바뀌었으면 409 → 로그아웃된 척하지 않고 바뀐 계정을
    // 다시 읽는다(리뷰 10·11·43차)
    final me = Auth.me.value;
    if (me != null && !_anyAccount.contains(request.url.path)) {
      request.headers.putIfAbsent('x-kumoniji-account', () => '${me.id}');
    }
    final res = await _sendWithRetry(request as http.Request);
    if (res.statusCode == 403 && me != null && identical(Auth.me.value, me)) {
      final bytes = await res.stream.toBytes();
      // 다른 탭이 같은 계정으로 다시 로그인해 2단계 인증 전 — 이 탭도 내 정보를 다시 읽어 인증 화면으로(리뷰 25차)
      if (_code(bytes) == 'mfa') Auth.reloadIfStill(me);
      return http.StreamedResponse(Stream.value(bytes), 403, headers: res.headers, request: res.request);
    }
    if (res.statusCode != 409) return res;
    final bytes = await res.stream.toBytes();
    // 이 요청이 지금 계정에서 나간 것일 때만 — 앞 계정 요청의 늦은 409가 이미 바뀐 계정을 다시 비우지 않게(리뷰 8차)
    final from = request.headers['x-kumoniji-account'];
    // 같은 계정으로 다시 로그인했어도 로그인마다 새 객체 — 옛 세션 요청의 늦은 409가 새 로그인을 비우지 않게(리뷰 22차).
    // 같은 세션의 다시 읽기가 넣은 새 객체는 같은 세션으로 본다(Auth._still)
    if (_code(bytes) == 'account_changed' && me != null && Auth._still(me) && from == '${me.id}') {
      Auth.me.value = null; // 먼저 비워야 다시 읽기(/me)에 옛 계정 번호가 안 붙는다
      Auth.reloadAfterSwitch();
    }
    return http.StreamedResponse(Stream.value(bytes), 409, headers: res.headers, request: res.request);
  }

  Future<http.StreamedResponse> _sendWithRetry(http.Request request) async {
    var (status, bytes, first) = await _read(await _send(request));
    // 403 csrf(로그인 포함 — 비밀번호 확인 전에 거절되니 실패가 쌓이지 않는다): 다른 탭이 CSRF 쿠키를 새로 받아 덮어씀 — 이 탭이 기억한 값을 버리고 지금 쿠키 값으로 한 번 더
    if (status == 403 && kIsWeb && _code(bytes) == 'csrf') {
      _csrf = null;
      _csrfFetch = null;
      // 다시 보낸 결과도 아래 401 처리를 거친다 — 액세스도 만료됐으면 갱신 뒤 한 번 더(리뷰 51차)
      (status, bytes, first) = await _read(await _send(_copy(request)));
    }
    final again = http.StreamedResponse(Stream.value(bytes), status, headers: first.headers, request: first.request);
    // 세션이 끝난 401(code: session)만 갱신한다. 틀린 MFA 코드·비밀번호(credentials)를 다시 보내면 실패가 두 번 쌓인다.
    if (status != 401 || _code(bytes) != 'session' || _noRetry.contains(request.url.path) || !await refresh()) {
      return again;
    }
    return _send(_copy(request));
  }

  static Future<(int, List<int>, http.StreamedResponse)> _read(http.StreamedResponse r) async =>
      (r.statusCode, await r.stream.toBytes(), r);

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
    // 메일(인증·재설정) 언어는 서버가 Accept-Language로 정한다 — 화면 언어(고른 언어, 없으면 기기 언어).
    // 휴대폰의 HTTP 클라이언트는 이 머리글을 스스로 붙이지 않는다.
    r.headers['accept-language'] = Settings.lang;
    // 실제로 보내기 직전에 한 번 더 — 웹은 CSRF 값을 기다리는 사이 판 화면이 닫힐 수 있다(리뷰 35차)
    if (r is GuardedRequest && !r.wanted()) throw http.ClientException('no longer wanted', r.url);
    // 시간이 지나면 요청 자체를 끊는다(브라우저면 XHR 중단) — 기다리기만 그만두면 늦게 온 응답의 Set-Cookie가
    // 그사이 로그인한 다른 계정의 쿠키를 덮을 수 있다(리뷰 28차).
    // 세션 갱신도 끊는다 — 서버가 회전한 뒤 응답을 못 받아도, 서버는 같은 옛 토큰에 같은 새 토큰을 다시 주므로(멱등
    // 갱신, 10분) 다음 갱신이 재사용으로 판정돼 모든 기기가 로그아웃되지 않는다(리뷰 30·40·48차)
    final abort = Completer<void>();
    final timer = Timer(timeout, () => abort.isCompleted ? null : abort.complete());
    final req = http.AbortableRequest(r.method, r.url, abortTrigger: abort.future)
      ..headers.addAll(r.headers)
      ..bodyBytes = r.bodyBytes;
    try {
      return await _whole(req).timeout(timeout);
    } finally {
      timer.cancel();
    }
  }

  /// 머리글과 본문을 다 받을 때까지 — 머리글 뒤 본문에서 멈춰도 제한에 걸리게(리뷰 24차)
  Future<http.StreamedResponse> _whole(http.BaseRequest r) async {
    final res = await inner.send(r);
    final bytes = await res.stream.toBytes();
    return http.StreamedResponse(
      Stream.value(bytes),
      res.statusCode,
      contentLength: bytes.length,
      headers: res.headers,
      request: res.request,
      reasonPhrase: res.reasonPhrase,
    );
  }

  /// 다시 보낼 사본 — 보내는 쪽이 더는 원하지 않으면(판 화면이 닫힘) 보내지 않는다(리뷰 34차)
  http.Request _copy(http.Request r) {
    if (r is GuardedRequest && !r.wanted()) throw http.ClientException('no longer wanted', r.url);
    return (r is GuardedRequest ? GuardedRequest(r.method, r.url, r.wanted) : http.Request(r.method, r.url))
      ..headers.addAll(r.headers)
      ..bodyBytes = r.bodyBytes;
  }

  /// 실패하면 다음 요청에서 다시 받는다(실패한 Future를 계속 재사용하면 새로고침 전까지 모든 요청이 막힌다).
  Future<String> _getCsrf() => _csrfFetch ??= _fetchCsrf().catchError((Object e) {
    _csrfFetch = null;
    throw e;
  });

  Future<String> _fetchCsrf() async {
    // 시간이 지나면 요청 자체를 끊는다 — 늦은 응답의 Set-Cookie가 그 뒤 받은 재시도 키 쿠키를 덮지 않게(리뷰 64차)
    final abort = Completer<void>();
    final timer = Timer(timeout, () => abort.isCompleted ? null : abort.complete());
    final http.StreamedResponse res;
    try {
      res = await _whole(
        http.AbortableRequest('GET', Uri.parse('${Api.base}/api/auth/csrf'), abortTrigger: abort.future),
      ).timeout(timeout);
    } finally {
      timer.cancel();
    }
    final r = await http.Response.fromStream(res);
    if (r.statusCode != 200) throw http.ClientException('csrf ${r.statusCode}');
    return jsonDecode(r.body)['csrf'] as String;
  }

  /// 리프레시 토큰으로 새 액세스(회전). 실패하면 로그아웃 상태. 요청은 제한 시간에 끊긴다(_send).
  /// 앱은 진행 중인 갱신을 토큰마다 — 멈춘 A의 갱신이 그 뒤 로그인한 B의 갱신을 막지 않게(리뷰 42차).
  /// 웹은 쿠키 하나를 탭이 같이 쓰니 하나로 모은다
  Future<bool> refresh() {
    if (_refreshing == null || (!kIsWeb && _refreshingFor != _refresh)) {
      late final Future<bool> f;
      f = _doRefresh().whenComplete(() {
        if (identical(_refreshing, f)) _refreshing = null;
      });
      _refreshing = f;
      _refreshingFor = _refresh;
    }
    return _refreshing!;
  }

  String? _refreshingFor;

  /// 갱신 재시도 키 — 메모리에만 둔다. 응답을 못 받고 끊긴 갱신은 같은 키로 다시 보내 서버가 같은 새 토큰을 다시
  /// 주게 하고(멱등), 응답을 받으면 버린다. 저장된 토큰을 훔친 사람은 이 키를 몰라 다시 받지 못한다(리뷰 48·50차)
  /// 보낸 토큰마다(웹은 쿠키라 하나) — 멈춘 A의 응답이 B의 키를 지우지 않게(리뷰 52차)
  final _retry = <String?, String>{};

  Future<bool> _doRefresh() async {
    if (!kIsWeb && _refresh == null) return false;
    final sent = _refresh; // 보낸 토큰 — 응답이 늦게 오는 사이 로그아웃·다른 계정 로그인으로 바뀌었으면 결과를 버린다(리뷰 41차)
    // 웹은 보내지 않는다 — 서버가 브라우저마다 심은 HttpOnly 쿠키를 키로 써서 다른 탭·새로고침도 같은 키다(리뷰 60·62차)
    final retry = _retry[sent] ??= base64UrlEncode(List.generate(24, (_) => Random.secure().nextInt(256)));
    http.Request req() => http.Request('POST', Uri.parse('${Api.base}/api/auth/refresh'))
      ..headers['content-type'] = 'application/json'
      ..body = jsonEncode({if (!kIsWeb) 'refresh': sent, if (!kIsWeb) 'retry': retry});
    var r = await _send(req());
    // 403: 갱신 전에 CSRF로 거절됨(다른 탭이 CSRF 쿠키를 바꿈) — 새 값으로 같은 키 그대로 한 번 더(리뷰 53차)
    if (r.statusCode == 403 && kIsWeb) {
      _csrf = null;
      _csrfFetch = null;
      r = await _send(req());
    }
    final body = await r.stream.bytesToString();
    // 비교는 마지막 await 뒤, 저장 바로 앞에서 — 그사이 로그인한 B의 토큰을 덮거나 지우지 않게(리뷰 41·54차)
    if (!kIsWeb && _refresh != sent) return false;
    // 키는 서버가 처리한 게 확실하고 결과를 반영한 뒤에만 버린다(200 새 토큰 저장·401 세션 없음·409 남이 갱신).
    // 5xx(프록시 502·504 포함)는 회전을 커밋했을 수 있고, 403은 처리 전 거절, 200인데 토큰이 깨졌으면 못 받은 것과
    // 같아 같은 키로 다시 보내야 한다(리뷰 51·53·54차). 이때는 세션이 끝난 게 아니니 토큰을 두고 던진다(리뷰 46차)
    void drop() => _retry[sent] == retry ? _retry.remove(sent) : null;
    final j = r.statusCode == 200 && !kIsWeb ? _tokens(body) : null;
    // 세션이 끝났다고 확실한 건 401뿐 — 429(요청 제한) 같은 다른 거절도 토큰을 두고 던진다(리뷰 53차)
    final unsure = r.statusCode != 200 && r.statusCode != 401 && r.statusCode != 409;
    if (unsure || (r.statusCode == 200 && !kIsWeb && j == null)) {
      throw http.ClientException('refresh ${r.statusCode}', r.request?.url);
    }
    // 409: 다른 탭이 방금 같은 쿠키를 갱신함 — 그 탭의 응답이 새 쿠키를 심을 때까지 잠깐 기다린 뒤 공유 쿠키로 다시 시도
    if (r.statusCode == 409) {
      drop();
      await Future.delayed(raceWait);
      return true;
    }
    if (r.statusCode != 200) {
      drop();
      keep(null);
      return false;
    }
    keep(j);
    drop();
    return true;
  }

  /// 갱신 응답의 토큰 — 둘 다 문자열이 아니면 null(본문이 비었거나 깨짐)
  static Map<String, dynamic>? _tokens(String body) {
    try {
      final j = jsonDecode(body);
      return j is Map<String, dynamic> && j['access'] is String && j['refresh'] is String ? j : null;
    } catch (_) {
      return null;
    }
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
  static final me = ValueNotifier<Me?>(null)..addListener(() => _meChanges++);

  /// me가 바뀐 횟수 — 기다리는 사이 로그인·로그아웃이 있었는지(값만 보면 로그인했다 로그아웃한 것을 모른다)
  static int _meChanges = 0;
  static int _loads = 0; // 로그인 상태를 처음부터 읽은 횟수(로그인·인증 완료·시작) — 그사이 다시 로그인했는지 본다

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

  /// 지금 쿠키(웹)·토큰(앱)의 계정. 로그인이 없다고 확실할 때만 null — /me가 401이고 서버가 갱신도 거절했을 때.
  /// 모르면 던진다(5xx·연결 오류·제한 시간, 그리고 갱신됐거나 다른 탭이 방금 갱신(409)했는데 새 쿠키가 아직 안 와
  /// /me가 여전히 401) — 부르는 쪽이 잠시 뒤 다시 읽는다. 유효한 세션을 끝난 것으로 보지 않게(리뷰 31·55·56차)
  static Future<Me?> _current() async {
    var r = await client.get(_uri('/me'));
    if (r.statusCode == 401) {
      if (!await client.refresh()) return null;
      r = await client.get(_uri('/me'));
    }
    if (r.statusCode == 200) return Me.fromJson(_decode(r));
    throw AuthError(r.statusCode);
  }

  /// 시작할 때: 로그인돼 있는지. 모르면(장애 등) 로그인 화면을 보여 주되 뒤에서 될 때까지 다시 읽어, 복구되면
  /// 저절로 홈으로(리뷰 55차).
  static Future<Me?> load() async {
    _loads++;
    // 기다리는 사이 다른 쪽(뒤의 복구·로그인·로그아웃)이 계정을 바꿨으면 늦은 결과로 덮지 않는다 — 로그아웃한 뒤
    // 옛 세션의 응답이 홈을 다시 여는 일이 없게(리뷰 화폐 재리뷰)
    final start = _meChanges;
    try {
      final m = await _current();
      if (_meChanges == start) me.value = m;
    } catch (_) {
      if (_meChanges == start) {
        me.value = null;
        reloadAfterSwitch();
      }
    }
    return me.value;
  }

  /// 로그인한 채 서버 상태를 바꾼 뒤(2단계 인증 켜기·끄기·구글 연결 해제 등) 내 정보를 다시 읽는다. 모르면(5xx·
  /// 시간 초과) 지금 계정을 그대로 두고 뒤에서 다시 — load()처럼 비우면 AuthGate가 계정 화면과 그 위 대화상자(한 번만
  /// 보이는 복구 코드 등)를 걷어 버린다(리뷰 39차). 세션이 끝났다고 확실할 때만(_current가 null) 비운다.
  static Future<void> reload() async {
    final session = me.value;
    if (session == null) {
      await load();
      return;
    }
    try {
      final n = ++_reads, loads = _loads;
      _applyRead(n, loads, session, await _current());
    } catch (_) {
      reloadIfStill(session);
    }
  }

  static int _reads = 0, _applied = 0; // 내 정보 다시 읽기 순번 — 늦게 끝난 옛 읽기가 새 읽기를 덮지 않게
  static final _roots = Expando<Me>(); // 다시 읽기로 넣은 객체 → 그 세션을 연 로그인 객체

  /// 다시 읽은 결과를 넣되, 그사이 세션이 그대로일 때만(리뷰 26차). 같은 세션의 다른 다시 읽기가 이미 넣은 값이면
  /// 더 나중에 시작한 읽기만 덮는다 — 설정을 바꾸기 전에 떠난 읽기가 늦게 와도 바꾼 뒤의 읽기가 이긴다(리뷰 45차)
  // 세션이 그대로인지 — 같은 로그인에서 이어진 다시 읽기 객체(같은 계정)끼리는 그대로로 본다. 앞 읽기가 다른 계정(다른
  // 탭이 바꾼 쿠키)을 넣었으면 옛 계정에서 떠난 읽기가 되돌리지 못하게(리뷰 46차), 같은 계정으로 다시 로그인했으면 옛
  // 로그인의 요청이 새 세션을 건드리지 못하게(화폐 재리뷰) 계정 ID가 아니라 로그인 객체로 비교한다
  static Me _rootOf(Me m) => _roots[m] ?? m;
  static bool _still(Me session) {
    final now = me.value;
    return now != null && identical(_rootOf(now), _rootOf(session));
  }

  // 읽는 사이 직접 로그인을 시작했으면(load) 버린다 — 옛 세션 읽기가 먼저 와 새 로그인 결과를 밀어내지 않게(화폐 재리뷰)
  static void _applyRead(int n, int loads, Me session, Me? m) {
    if (!_still(session) || n < _applied || _loads != loads) return;
    _applied = n;
    if (m != null && m.id == session.id) _roots[m] = _rootOf(session);
    me.value = m;
  }

  /// 내 정보를 다시 읽되 그사이 세션이 그대로일 때만 반영 — 인증을 마치거나 다른 계정으로 로그인한 뒤 늦은 응답이
  /// 덮지 않게(리뷰 26차). 모르면 세션이 그대로인 동안 다시(최대 30초 간격, 리뷰 27차)
  /// 남는 틈(알고 둠, 11-26 사용자 결정 1번 — 서버 sessions.refresh 주석과 같은 것): 웹에서 이 루프의 갱신 응답이
  /// 날아가는 사이 같은 브라우저에서 다른 계정으로 로그인하면, 늦게 온 Set-Cookie가 새 로그인을 덮을 수 있다. 쿠키는
  /// 브라우저가 응답을 받는 즉시 적용해 앱이 막을 수 없고, 요청 제한 시간(15초) 안의 일이며 같은 브라우저 안에서만
  /// 일어난다(다른 사람에게 토큰이 가지 않음, 리뷰 37차 ①).
  static Future<void> reloadIfStill(Me session) async {
    // 다른 다시 읽기가 같은 세션의 새 객체를 넣었어도 계속 — 설정을 바꾼 뒤의 읽기가 실패하면 옛 값이 남는다(리뷰 화폐 재리뷰)
    for (var wait = 1; _still(session); wait = wait * 2 > 30 ? 30 : wait * 2) {
      try {
        final n = ++_reads, loads = _loads;
        _applyRead(n, loads, session, await _current());
        return;
      } catch (_) {}
      await Future.delayed(Duration(seconds: wait));
    }
  }

  /// 다른 탭이 계정을 바꾼 뒤 지금 쿠키의 계정을 읽는다. 모르면 될 때까지 다시(최대 30초 간격) — 한 번 실패로 유효한
  /// 쿠키를 두고 로그인 화면에 남지 않게(리뷰 15·16차). 로그인이 없다고 확실하거나 그사이 로그인·로그아웃하면 그만둔다.
  static Future<void> reloadAfterSwitch() async {
    // 그사이 직접 로그인을 시작했으면(load, 아직 응답 전이라 me가 그대로여도) 그만둔다 — 옛 계정 응답이 먼저 와 새
    // 로그인 결과를 버리게 하지 않게(화폐 재리뷰)
    final start = _meChanges, loads = _loads;
    bool still() => _meChanges == start && _loads == loads;
    for (var wait = 1; me.value == null && still(); wait = wait * 2 > 30 ? 30 : wait * 2) {
      try {
        // 응답이 멈추면 AuthClient.timeout이 예외로 끝내 다시 시도로(리뷰 21차)
        final m = await _current();
        // 기다리는 사이 직접 로그인함(그 뒤 로그아웃했어도) — 늦은 응답으로 덮지 않는다(리뷰 17·42차)
        if (still() && m != null) me.value = m;
        return;
      } catch (_) {}
      await Future.delayed(Duration(seconds: wait));
    }
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
    await reload();
  }

  static Future<void> logout() async {
    final loads = _loads, id = me.value?.id;
    try {
      await _post('/logout');
    } on AuthError catch (e) {
      // 다른 탭에서 계정이 바뀜 — 아무것도 폐기되지 않았다. 로그아웃된 척하지 않고 바뀐 계정을 다시 읽은 채 둔다(리뷰 11차)
      if (e.code == 'account_changed') return;
      // 그 밖의 거절(CSRF 403 등)은 서버가 폐기하지 않았으니 던진다(리뷰 44차)
      if (e.status != 401) rethrow;
      // 401이어도 세션이 끝났다고 단정하지 않는다 — 액세스만 만료되고 다른 탭의 갱신 쿠키가 늦게 올 수도 있다.
      // 서버가 갱신을 거절(세션 없음)했을 때만 로그아웃 상태로. 갱신됨·다른 탭이 방금 갱신(409)이면 세션이 살아 있으니
      // 실패로 알리고, 장애(5xx·연결 오류)는 모르는 것이니 그대로 던진다(리뷰 47·48·52차)
      if (await client.refresh()) rethrow;
    }
    // 연결 끊김·시간 초과는 그대로 던진다 — 서버가 세션을 폐기했는지 모르고, 웹의 HttpOnly 쿠키는 서버 응답으로만
    // 지워져 로그아웃된 척하면 새로고침에 다시 로그인된다. 호출부가 실패를 알린다(리뷰 37·38차)
    // 기다리는 사이 다시 로그인했거나 계정이 바뀌었으면 늦은 응답으로 새 로그인을 지우지 않는다(리뷰 52차). 같은 세션의
    // 내 정보 다시 읽기는 객체만 바꾸니 객체가 아니라 로그인 횟수·계정으로 본다(리뷰 54차)
    if (_loads != loads || me.value?.id != id) return;
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
    await reload();
    return List<String>.from(j['recovery_codes']);
  }

  static Future<void> mfaDisable(String code) async {
    await _post('/mfa/disable', {'code': code});
    await reload();
  }

  static Future<List<String>> newRecoveryCodes() async =>
      List<String>.from((await _post('/mfa/recovery'))['recovery_codes']);

  static Future<void> unlinkGoogle() async {
    await _post('/google/unlink');
    await reload();
  }

  static Future<void> deleteAccount() async {
    await _post('/delete');
    client.keep(null);
    me.value = null;
  }

  /// 웹에서 구글로 보낼 주소(서버가 PKCE·state·nonce를 만든다).
  static String googleStart({bool link = false, bool reauth = false}) =>
      '${Api.base}/api/auth/google/start?lang=${Settings.lang}${link
          ? '&link=true'
          : reauth
          ? '&reauth=true'
          : ''}';
}
