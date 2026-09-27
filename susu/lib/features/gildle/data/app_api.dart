import 'package:dio/dio.dart';

/// suvisdev/apps/gildle/adapter/inbound/api/v1/{app_router,push_token_router}.py
class AppApi {
  const AppApi(this._dio);

  final Dio _dio;

  Future<AppVersionInfo> version() async {
    final resp = await _dio.get('/api/gildle/app/version', queryParameters: {'platform': 'android'});
    return AppVersionInfo.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> registerPushToken(String token) =>
      _dio.post('/api/gildle/push-tokens', data: {'token': token, 'platform': 'android'});

  Future<void> unregisterPushToken(String token) =>
      _dio.delete('/api/gildle/push-tokens', data: {'token': token});
}

class AppVersionInfo {
  const AppVersionInfo({required this.minVersion, required this.latestVersion, this.storeUrl});

  final String minVersion;
  final String latestVersion;
  final String? storeUrl;

  factory AppVersionInfo.fromJson(Map<String, dynamic> json) => AppVersionInfo(
        minVersion: json['min_version'] as String,
        latestVersion: json['latest_version'] as String,
        storeUrl: json['store_url'] as String?,
      );

  /// "1.2.3" 식 세미버전 비교 — current < minVersion 이면 true.
  bool requiresUpdate(String current) => compareVersions(current, minVersion) < 0;

  static int compareVersions(String a, String b) {
    final pa = a.split('+').first.split('.').map((s) => int.tryParse(s) ?? 0).toList();
    final pb = b.split('+').first.split('.').map((s) => int.tryParse(s) ?? 0).toList();
    for (var i = 0; i < 3; i++) {
      final x = i < pa.length ? pa[i] : 0;
      final y = i < pb.length ? pb[i] : 0;
      if (x != y) return x.compareTo(y);
    }
    return 0;
  }
}
