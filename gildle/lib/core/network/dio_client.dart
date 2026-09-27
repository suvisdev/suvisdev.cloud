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
      onError: (error, handler) async {
        debugPrint(
          '[Dio] ${error.requestOptions.method} ${error.requestOptions.path} '
          '-> ${error.response?.statusCode ?? '-'} ${error.message}',
        );
        // access token 만료(10분) — refresh 성공 시 같은 요청을 한 번만 다시 보낸다.
        final options = error.requestOptions;
        if (error.response?.statusCode == 401 && options.extra['retried'] != true) {
          if (await AuthSession.refresh()) {
            final token = await AuthSession.readAccessToken();
            options.headers['Authorization'] = 'Bearer $token';
            options.extra['retried'] = true;
            try {
              return handler.resolve(await dio.fetch(options));
            } on DioException catch (e) {
              return handler.next(e);
            }
          }
        }
        handler.next(error);
      },
    ),
  );

  return dio;
}

final dioProvider = Provider<Dio>((ref) => createDio());
