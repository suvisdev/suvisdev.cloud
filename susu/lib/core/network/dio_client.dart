import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../config/env.dart';

/// 임시 개발용 토큰 — 실제 로그인 JWT 발급 흐름이 이 화면 뒤로 연결되기 전까지
/// Authorization 헤더에 넣을 자리만 마련해둔다. 지금 쓰는 /mova/chat 자체는
/// 인증을 요구하지 않는다(백엔드 라우터 확인 완료) — 이후 인증 필요한
/// 엔드포인트가 추가되면 이 슬롯이 그대로 쓰인다.
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
      onRequest: (options, handler) {
        if (_devAuthToken.isNotEmpty) {
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
