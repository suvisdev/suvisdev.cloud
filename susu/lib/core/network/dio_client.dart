import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth.dart';
import '../config/env.dart';

/// 로그인 세션(카카오 모바일 JWT)이 있으면 그 access token을 Authorization
/// 헤더에 싣는다. 없으면(로그인 전 화면 등) 개발용 토큰(DEV_AUTH_TOKEN)
/// 슬롯으로 폴백 — /mova/chat처럼 인증 불필요한 엔드포인트에는 영향 없다.
const String _devAuthToken = String.fromEnvironment('DEV_AUTH_TOKEN');

Dio createDio() {
  final dio = Dio(
    BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final sessionToken = await AuthSession.readAccessToken();
        if (sessionToken != null && sessionToken.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $sessionToken';
        } else if (_devAuthToken.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $_devAuthToken';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        debugPrint(
          '[Dio] ${error.requestOptions.method} ${error.requestOptions.path} '
          '-> ${error.response?.statusCode ?? '-'} ${error.message}',
        );
        handler.next(error);
      },
    ),
  );

  return dio;
}

final dioProvider = Provider<Dio>((ref) => createDio());
