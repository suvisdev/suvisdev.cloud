import 'package:dio/dio.dart';

import '../domain/geo_point.dart';
import '../domain/season_mode.dart';
import 'models/route_option.dart';

/// suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py — 인증 불필요.
/// 경로 계산은 백엔드(OSM 보행 그래프 + 그늘 점수)가 하고, 앱은 결과만 그린다.
/// 웹(`suvis/lib/gildle-api.ts`)과 같은 엔드포인트만 쓴다(2026-09-30 웹·앱 통일).
class GildleRouteApi {
  const GildleRouteApi(this._dio);

  final Dio _dio;

  /// 경로 후보(빠른·그늘·푸른 길) + 고를 이유 + 경로 곁 반려동물 장소.
  Future<RouteOptionsResult> options({
    required GeoPoint start,
    required GeoPoint end,
    required SeasonMode mode,
  }) async {
    final resp = await _dio.post('/api/gildle/routes/options', data: _ends(start, end, mode));
    return RouteOptionsResult.fromJson(resp.data as Map<String, dynamic>);
  }

  /// 고른 장소에 들렀다 가는 경로 — `baseKind`와 같은 성격으로 계산한다.
  Future<RouteOption> via({
    required GeoPoint start,
    required GeoPoint end,
    required SeasonMode mode,
    required PetPlace place,
    required String baseKind,
  }) async {
    final resp = await _dio.post(
      '/api/gildle/routes/via',
      data: {
        ..._ends(start, end, mode),
        'via_lat': place.point.lat,
        'via_lng': place.point.lng,
        'via_name': place.name,
        'base_kind': baseKind,
      },
    );
    return RouteOption.fromJson(
      (resp.data as Map<String, dynamic>)['option'] as Map<String, dynamic>,
    );
  }

  /// 문장·시간·거리·선호(여러 개 가능)·들를 곳으로 산책 추천. 문장은 서버(7.8B + 규칙)가 이해한다.
  Future<WalkPlan> plan({
    required GeoPoint start,
    String? text,
    int? minutes,
    double? distanceKm,
    List<String> preferences = const [],
    List<String> stops = const [],
  }) async {
    final resp = await _dio.post(
      '/api/gildle/walk/plan',
      data: {
        'lat': start.lat,
        'lng': start.lng,
        'text': ?text,
        'minutes': ?minutes,
        'distance_km': ?distanceKm,
        if (preferences.isNotEmpty) 'preferences': preferences,
        if (stops.isNotEmpty) 'stops': stops,
      },
      // 문장 이해(7.8B)가 첫 호출엔 모델을 올리느라 오래 걸린다.
      options: Options(receiveTimeout: const Duration(seconds: 90)),
    );
    return WalkPlan.fromJson(resp.data as Map<String, dynamic>);
  }

  static Map<String, dynamic> _ends(GeoPoint start, GeoPoint end, SeasonMode mode) => {
        'start_lat': start.lat,
        'start_lng': start.lng,
        'end_lat': end.lat,
        'end_lng': end.lng,
        'mode': mode.apiValue,
      };
}
