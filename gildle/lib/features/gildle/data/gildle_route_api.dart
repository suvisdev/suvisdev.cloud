import 'package:dio/dio.dart';

import '../domain/geo_point.dart';
import '../domain/season_mode.dart';
import 'models/loop_candidate.dart';
import 'models/route_result.dart';

/// suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py — 인증 불필요.
/// 경로 계산은 백엔드(OSM 보행 그래프 + 그늘 점수)가 하고, 앱은 결과만 그린다.
class GildleRouteApi {
  const GildleRouteApi(this._dio);

  final Dio _dio;

  Future<RouteResult> route({
    required GeoPoint start,
    required GeoPoint end,
    required SeasonMode mode,
  }) async {
    final resp = await _dio.post(
      '/api/gildle/routes',
      data: {
        'start_lat': start.lat,
        'start_lng': start.lng,
        'end_lat': end.lat,
        'end_lng': end.lng,
        'mode': mode.apiValue,
      },
    );
    return RouteResult.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<LoopResult> loops({
    required GeoPoint start,
    required double targetM,
    required SeasonMode mode,
    int limit = 3,
  }) async {
    final resp = await _dio.post(
      '/api/gildle/loops',
      data: {
        'lat': start.lat,
        'lng': start.lng,
        'target_m': targetM,
        'mode': mode.apiValue,
        'limit': limit,
      },
    );
    return LoopResult.fromJson(resp.data as Map<String, dynamic>);
  }
}
