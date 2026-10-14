import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api_config.dart';
import 'core/config/env.dart';
import 'google_config.dart';

/// 모바일 세션(백엔드가 발급한 자체 JWT/refresh token) 저장소.
///
/// 웹 로그인과는 완전히 분리된 storage key를 쓴다 — gildle 앱(모바일)은 이 값만
/// 다루고, 서버 쪽 Redis 네임스페이스 분리(auth:refresh:mobile:{userId})와
/// 짝을 이룬다.
/// 로그인 여부 — 로그인 없이도 지도·경로 추천은 쓸 수 있고(2026-09-28, 심사·게스트),
/// 산책 기록 저장·기록 목록·내 정보만 로그인이 필요하다. 앱 시작 시 SplashScreen이 채운다.
final loggedInProvider = StateProvider<bool>((ref) => false);

const _termsUrl = 'https://suvisdev.cloud/terms';
const _privacyUrl = 'https://suvisdev.cloud/gildle/privacy';

class AuthSession {
  AuthSession._();

  static const _storage = FlutterSecureStorage();
  static const _accessTokenKey = 'suvis_mobile_access_token';
  static const _refreshTokenKey = 'suvis_mobile_refresh_token';

  /// 저장된 refresh token이 있으면 세션이 유지 중이라고 본다(로컬 판단).
  /// 서버 쪽에서 이미 만료·폐기됐을 수 있음을 감안해 실제 API 호출 시 401을
  /// 받으면 재로그인으로 유도하는 처리가 필요하지만, 이번 범위에서는 앱 시작
  /// 시점의 화면 분기(main.dart)에만 이 값을 쓴다.
  static Future<bool> hasStoredSession() async {
    final refreshToken = await _storage.read(key: _refreshTokenKey);
    return refreshToken != null && refreshToken.isNotEmpty;
  }

  /// 인증이 필요한 API 호출(산책 기록 등)의 Authorization 헤더에 쓴다.
  /// access token은 10분 TTL — 401을 받으면 dio 인터셉터가 [refresh]로 재발급해 재시도한다.
  static Future<String?> readAccessToken() async {
    return _storage.read(key: _accessTokenKey);
  }

  static Future<void>? _refreshing;

  /// POST /auth/mobile/refresh — refresh token은 로테이션되므로(재사용 감지 시 401)
  /// 둘 다 새로 저장한다. 동시 401이 여러 건 나도 재발급은 한 번만 돈다.
  /// 실패(만료·폐기)하면 로컬 세션을 지우고 false — 호출자는 로그인 화면으로 보낸다.
  static Future<bool> refresh() async {
    final inFlight = _refreshing;
    if (inFlight != null) {
      await inFlight;
      return (await readAccessToken())?.isNotEmpty ?? false;
    }
    final task = _refreshOnce();
    _refreshing = task.then((_) {}, onError: (_) {});
    try {
      return await task;
    } finally {
      _refreshing = null;
    }
  }

  static Future<bool> _refreshOnce() async {
    final refreshToken = await _storage.read(key: _refreshTokenKey);
    if (refreshToken == null || refreshToken.isEmpty) return false;
    try {
      final resp = await http.post(
        Uri.parse('$authBaseUrl/auth/mobile/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': refreshToken}),
      );
      if (resp.statusCode != 200) {
        if (resp.statusCode == 401) await clear();
        return false;
      }
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      await save(
        accessToken: body['access_token'] as String,
        refreshToken: body['refresh_token'] as String,
      );
      return true;
    } catch (_) {
      return false; // 네트워크 오류 — 세션은 남겨 두고 이번 호출만 실패
    }
  }

  static Future<void> save({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  static Future<void> clear() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }

  /// 회원 탈퇴(Google Play 계정 삭제 정책) — ① gildle 데이터(산책 기록·기기 토큰)
  /// ② 계정 자체(인증 게이트웨이) 순서로 지우고 로컬 세션을 비운다. 실패하면 예외.
  static Future<void> deleteAccount() async {
    Future<http.Response> send(Future<http.Response> Function(String token) call) async {
      var token = await readAccessToken() ?? '';
      var resp = await call(token);
      if (resp.statusCode == 401 && await refresh()) {
        token = await readAccessToken() ?? '';
        resp = await call(token);
      }
      return resp;
    }

    final data = await send(
      (t) => http.delete(
        Uri.parse('${AppConfig.apiBaseUrl}/api/gildle/me/data'),
        headers: {'Authorization': 'Bearer $t'},
      ),
    );
    if (data.statusCode != 200) {
      throw Exception('산책 기록을 지우지 못했습니다(${data.statusCode}).');
    }
    final account = await send(
      (t) => http.delete(
        Uri.parse('$authBaseUrl/auth/mobile/account'),
        headers: {'Authorization': 'Bearer $t'},
      ),
    );
    if (account.statusCode != 204) {
      throw Exception('계정을 삭제하지 못했습니다(${account.statusCode}).');
    }
    await clear();
  }

  /// 서버 쪽 refresh token 폐기(POST /auth/mobile/logout) 시도 후 로컬 세션을
  /// 지운다. 서버 호출이 실패해도(네트워크 등) 로컬 로그아웃은 항상 진행한다 —
  /// best-effort revoke.
  static Future<void> logout() async {
    final refreshToken = await _storage.read(key: _refreshTokenKey);
    if (refreshToken != null && refreshToken.isNotEmpty) {
      try {
        await http.post(
          Uri.parse('$authBaseUrl/auth/mobile/logout'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh_token': refreshToken}),
        );
      } catch (_) {
        // 서버 revoke는 best-effort — 실패해도 아래 clear()로 로컬은 항상 로그아웃.
      }
    }
    await clear();
  }
}

/// 로그인·회원가입 화면 — 카카오·구글 또는 이메일. 필요한 곳(산책 기록 저장·기록·내 정보)에서
/// push로 열고, 성공하면 `true`로 닫힌다. 이메일 가입은 필수 항목(이메일·비밀번호)과
/// 필수 동의만 받는다(2026-09-28).
class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  bool _isLoading = false;
  String? _errorMessage;
  bool _signupMode = false;
  bool _agreed = false;
  final _email = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action, String failPrefix) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      await action();
      ref.read(loggedInProvider.notifier).state = true;
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _errorMessage = '$failPrefix: ${e is _AuthError ? e.message : e}');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleKakaoLogin() => _run(() async {
        final accessToken = await _obtainKakaoAccessToken();
        await _loginWithBackend(accessToken);
      }, '카카오 로그인에 실패했습니다');

  Future<void>? _googleInit;

  /// 구글 로그인 — id token만 받아 POST /auth/google/mobile로 보낸다(검증은 서버가).
  /// 같은 이메일로 이미 가입된 계정이 있으면 서버가 409를 준다(2026-10-02 결정).
  Future<void> _handleGoogleLogin() => _run(() async {
        final signIn = GoogleSignIn.instance;
        await (_googleInit ??= signIn.initialize(serverClientId: googleServerClientId));
        final GoogleSignInAccount account;
        try {
          account = await signIn.authenticate();
        } on GoogleSignInException catch (e) {
          if (e.code == GoogleSignInExceptionCode.canceled) {
            throw const _AuthError('로그인을 취소했습니다.');
          }
          rethrow;
        }
        final idToken = account.authentication.idToken;
        if (idToken == null) throw const _AuthError('구글 인증 정보를 받지 못했습니다.');
        final resp = await http.post(
          Uri.parse('$authBaseUrl/auth/google/mobile'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'id_token': idToken}),
        );
        if (resp.statusCode == 409) {
          await signIn.signOut();
          throw const _AuthError('이미 가입된 이메일입니다. 기존 방법(이메일·카카오)으로 로그인해 주세요.');
        }
        if (resp.statusCode != 200) throw _AuthError('서버 오류(${resp.statusCode})');
        await _saveTokens(resp.body);
      }, '구글 로그인에 실패했습니다');

  Future<void> _handleEmail() async {
    final email = _email.text.trim().toLowerCase();
    final password = _password.text;
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email)) {
      setState(() => _errorMessage = '이메일 형식을 확인해 주세요.');
      return;
    }
    if (password.length < 8) {
      setState(() => _errorMessage = '비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (_signupMode && !_agreed) {
      setState(() => _errorMessage = '이용약관과 개인정보처리방침에 동의해 주세요.');
      return;
    }
    await _run(() async {
      final path = _signupMode ? '/auth/mobile/signup' : '/auth/mobile/login';
      final resp = await http.post(
        Uri.parse('$authBaseUrl$path'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );
      if (resp.statusCode == 409) throw const _AuthError('이미 가입된 이메일입니다. 로그인해 주세요.');
      if (resp.statusCode == 401) throw const _AuthError('이메일 또는 비밀번호가 올바르지 않습니다.');
      if (resp.statusCode != 200 && resp.statusCode != 201) {
        throw _AuthError('서버 오류(${resp.statusCode})');
      }
      await _saveTokens(resp.body);
    }, _signupMode ? '회원가입에 실패했습니다' : '로그인에 실패했습니다');
  }

  /// 카카오톡 앱으로 로그인을 시도하고, 미설치거나 실패하면 카카오계정 로그인으로
  /// 폴백한다. ※ 여기서 UserApi.instance.me()를 호출하지 않는다 — 유저정보 조회는
  /// 백엔드가 access_token을 kapi로 검증하며 단독 수행한다(중복 조회 방지).
  Future<String> _obtainKakaoAccessToken() async {
    OAuthToken token;
    if (await isKakaoTalkInstalled()) {
      try {
        token = await UserApi.instance.loginWithKakaoTalk();
      } catch (_) {
        token = await UserApi.instance.loginWithKakaoAccount();
      }
    } else {
      token = await UserApi.instance.loginWithKakaoAccount();
    }
    return token.accessToken;
  }

  /// POST /auth/kakao/mobile — access_token만 보내고, 백엔드가 내려준 자체
  /// JWT/refresh token을 secure storage에 저장한다.
  Future<void> _loginWithBackend(String kakaoAccessToken) async {
    final resp = await http.post(
      Uri.parse('$authBaseUrl/auth/kakao/mobile'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'access_token': kakaoAccessToken}),
    );
    if (resp.statusCode != 200) {
      throw _AuthError('서버 오류(${resp.statusCode})');
    }
    await _saveTokens(resp.body);
  }

  Future<void> _saveTokens(String rawBody) async {
    final body = jsonDecode(rawBody) as Map<String, dynamic>;
    await AuthSession.save(
      accessToken: body['access_token'] as String,
      refreshToken: body['refresh_token'] as String,
    );
  }

  Future<void> _open(String url) async {
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final muted = isDark ? const Color(0xFFB3B3B3) : const Color(0xFF737373);

    return Scaffold(
      appBar: AppBar(title: Text(_signupMode ? '회원가입' : '로그인')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              '산책 기록을 저장하려면 로그인하세요',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: muted),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _handleKakaoLogin,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFEE500),
                  foregroundColor: const Color(0xFF191919),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  elevation: 0,
                ),
                child: const Text(
                  '카카오로 계속하기',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                ),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: _isLoading ? null : _handleGoogleLogin,
                style: OutlinedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: const Color(0xFF1F1F1F),
                  side: const BorderSide(color: Color(0xFF747775)),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: const Text(
                  'Google로 계속하기',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                const Expanded(child: Divider()),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text('또는 이메일', style: TextStyle(fontSize: 12, color: muted)),
                ),
                const Expanded(child: Divider()),
              ],
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              autofillHints: const [AutofillHints.email],
              decoration: const InputDecoration(labelText: '이메일', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password,
              obscureText: true,
              autofillHints: [_signupMode ? AutofillHints.newPassword : AutofillHints.password],
              decoration: const InputDecoration(
                labelText: '비밀번호(8자 이상)',
                border: OutlineInputBorder(),
              ),
            ),
            if (_signupMode) ...[
              const SizedBox(height: 8),
              CheckboxListTile(
                value: _agreed,
                onChanged: _isLoading ? null : (v) => setState(() => _agreed = v ?? false),
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: const Text('(필수) 이용약관·개인정보처리방침에 동의합니다', style: TextStyle(fontSize: 13)),
              ),
              Wrap(
                spacing: 8,
                children: [
                  TextButton(onPressed: () => _open(_termsUrl), child: const Text('이용약관 보기')),
                  TextButton(onPressed: () => _open(_privacyUrl), child: const Text('개인정보처리방침 보기')),
                ],
              ),
            ],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _isLoading ? null : _handleEmail,
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
              child: _isLoading
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(_signupMode ? '가입하기' : '이메일로 로그인'),
            ),
            TextButton(
              onPressed: _isLoading
                  ? null
                  : () => setState(() {
                        _signupMode = !_signupMode;
                        _errorMessage = null;
                      }),
              child: Text(_signupMode ? '이미 계정이 있어요 — 로그인' : '처음이에요 — 이메일로 가입'),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 8),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red, fontSize: 13),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _AuthError implements Exception {
  const _AuthError(this.message);
  final String message;
}

/// 로그인이 필요한 화면(기록·내 정보)에 대신 보여 주는 안내 — 누르면 로그인 화면.
class LoginPrompt extends StatelessWidget {
  const LoginPrompt({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.lock_outline, size: 40),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => Navigator.of(context).push<bool>(
                MaterialPageRoute(builder: (_) => const AuthScreen()),
              ),
              child: const Text('로그인 / 회원가입'),
            ),
          ],
        ),
      ),
    );
  }
}

/// 로그인이 필요하면 로그인 화면을 띄우고, 로그인돼 있거나 방금 로그인했으면 true.
Future<bool> ensureLoggedIn(BuildContext context, WidgetRef ref) async {
  if (ref.read(loggedInProvider)) return true;
  final ok = await Navigator.of(context).push<bool>(
    MaterialPageRoute(builder: (_) => const AuthScreen()),
  );
  return ok == true;
}
