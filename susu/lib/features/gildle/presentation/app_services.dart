import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../../core/network/dio_client.dart';
import '../data/app_api.dart';

final appApiProvider = Provider<AppApi>((ref) => AppApi(ref.watch(dioProvider)));

/// 앱 시작 시 한 번: 버전 검사 결과(업데이트 필요 여부). 실패하면 막지 않는다(null).
final versionCheckProvider = FutureProvider<AppVersionInfo?>((ref) async {
  try {
    final info = await ref.watch(appApiProvider).version();
    final current = (await PackageInfo.fromPlatform()).version;
    return info.requiresUpdate(current) ? info : null;
  } catch (e) {
    debugPrint('버전 확인 실패: $e');
    return null;
  }
});

/// FCM 토큰 등록 — 로그인 뒤 호출. google-services.json이 없거나 Firebase 초기화가
/// 실패해도 앱은 그대로 동작한다(푸시만 없음). 발송 코드는 아직 백엔드에 없다.
class PushRegistrar {
  PushRegistrar(this._api);

  final AppApi _api;
  String? _token;

  Future<void> register() async {
    try {
      await Firebase.initializeApp();
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission();
      final token = await messaging.getToken();
      if (token != null) await _send(token);
      messaging.onTokenRefresh.listen(_send);
    } catch (e) {
      debugPrint('FCM 등록 건너뜀: $e');
    }
  }

  Future<void> _send(String token) async {
    _token = token;
    try {
      await _api.registerPushToken(token);
    } catch (e) {
      debugPrint('푸시 토큰 등록 실패: $e');
    }
  }

  /// 로그아웃 때 — 서버 revoke와 같은 best-effort.
  Future<void> unregister() async {
    final token = _token;
    if (token == null) return;
    try {
      await _api.unregisterPushToken(token);
    } catch (_) {}
  }
}

final pushRegistrarProvider = Provider<PushRegistrar>((ref) => PushRegistrar(ref.watch(appApiProvider)));
