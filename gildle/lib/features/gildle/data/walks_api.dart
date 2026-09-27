import 'package:dio/dio.dart';

import '../domain/geo_point.dart';
import 'models/walk.dart';

/// suvisdev/apps/gildle/adapter/inbound/api/v1/walk_router.py — 전부 로그인 필수.
/// Authorization 헤더는 dio 인터셉터가 싣고, 401이면 refresh 후 재시도한다.
class WalksApi {
  const WalksApi(this._dio);

  final Dio _dio;

  /// 서버 상한(`_MAX_PATH_POINTS`)과 같다 — 넘치면 서버가 잘라내므로 미리 솎아 보낸다.
  static const maxPathPoints = 5000;

  Future<WalkDetail> create({
    required DateTime startedAt,
    required DateTime endedAt,
    required int distanceM,
    required int durationS,
    required List<GeoPoint> path,
    required String seasonMode,
    double? avgShadeScore,
  }) async {
    final resp = await _dio.post(
      '/api/gildle/walks',
      data: {
        'started_at': startedAt.toUtc().toIso8601String(),
        'ended_at': endedAt.toUtc().toIso8601String(),
        'distance_m': distanceM,
        'duration_s': durationS,
        'path': [for (final p in _thin(path)) [p.lat, p.lng]],
        'season_mode': seasonMode,
        'avg_shade_score': ?avgShadeScore,
      },
    );
    return WalkDetail.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<List<WalkSummary>> list({int limit = 50, int offset = 0}) async {
    final resp = await _dio.get(
      '/api/gildle/walks',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return (resp.data as List<dynamic>)
        .map((j) => WalkSummary.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<WalkDetail> detail(int id) async {
    final resp = await _dio.get('/api/gildle/walks/$id');
    return WalkDetail.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> delete(int id) => _dio.delete('/api/gildle/walks/$id');

  Future<WalkStats> stats() async {
    final resp = await _dio.get('/api/gildle/walks/stats');
    return WalkStats.fromJson(resp.data as Map<String, dynamic>);
  }

  /// 등간격 솎기 — 시작·끝은 보존한다.
  static List<GeoPoint> _thin(List<GeoPoint> path) {
    if (path.length <= maxPathPoints) return path;
    final step = path.length / maxPathPoints;
    final out = <GeoPoint>[for (var i = 0; i < maxPathPoints - 1; i++) path[(i * step).floor()]];
    out.add(path.last);
    return out;
  }
}
