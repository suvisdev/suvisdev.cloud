import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'api_config.dart';
import 'main.dart';

/// 모바일 세션(백엔드가 발급한 자체 JWT/refresh token) 저장소.
///
/// 웹 로그인과는 완전히 분리된 storage key를 쓴다 — susu(모바일)는 이 값만
/// 다루고, 서버 쪽 Redis 네임스페이스 분리(auth:refresh:mobile:{userId})와
/// 짝을 이룬다.
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

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isLoading = false;
  String? _errorMessage;

  Future<void> _handleKakaoLogin() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final accessToken = await _obtainKakaoAccessToken();
      await _loginWithBackend(accessToken);

      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const HomeScreen()),
        (route) => false,
      );
    } catch (e) {
      setState(() => _errorMessage = '카카오 로그인에 실패했습니다: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
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
      throw Exception('백엔드 로그인 실패(${resp.statusCode}): ${resp.body}');
    }

    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    await AuthSession.save(
      accessToken: body['access_token'] as String,
      refreshToken: body['refresh_token'] as String,
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0D0F14) : const Color(0xFFE8E8E8),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '길들',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                    color: isDark ? Colors.white : const Color(0xFF171717),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '계속하려면 카카오로 로그인하세요',
                  style: TextStyle(
                    fontSize: 14,
                    color: isDark ? const Color(0xFFB3B3B3) : const Color(0xFF737373),
                  ),
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _handleKakaoLogin,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFFEE500),
                      foregroundColor: const Color(0xFF191919),
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      elevation: 0,
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text(
                            '카카오로 로그인',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                          ),
                  ),
                ),
                if (_errorMessage != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    _errorMessage!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.red, fontSize: 13),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
