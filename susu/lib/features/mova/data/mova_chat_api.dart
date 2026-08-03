import 'package:dio/dio.dart';

import 'models/mova_chat_request.dart';
import 'models/mova_chat_response.dart';

/// suvisdev/apps/mova/adapter/inbound/api/v1/market_chat_router.py — POST /mova/chat.
/// 인증 불필요(라우터에 require_admin/JWT 의존성 없음, IP rate limit만 있음).
class MovaChatApi {
  final Dio _dio;

  const MovaChatApi(this._dio);

  Future<MovaChatResponse> chat(MovaChatRequest request) async {
    final resp = await _dio.post('/mova/chat', data: request.toJson());
    return MovaChatResponse.fromJson(resp.data as Map<String, dynamic>);
  }
}
