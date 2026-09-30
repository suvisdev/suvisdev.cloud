import 'package:dio/dio.dart';

import '../domain/geo_point.dart';

class PlaceResult {
  const PlaceResult({required this.name, required this.point});

  /// 전체 주소("여의도공원, 여의공원로, 영등포구, 서울, 대한민국").
  final String name;
  final GeoPoint point;

  /// 목록에서 고른 뒤 검색창에 남길 짧은 이름.
  String get shortName => name.split(',').first;
}

/// 장소·주소 검색(Nominatim) — 웹 지도 검색창과 같은 질의(서울 범위 먼저, 없으면 국내 전체).
/// Nominatim 이용 정책상 자동완성은 금지라 앱은 제출할 때만 부른다.
class PlaceSearchApi {
  PlaceSearchApi()
      : _dio = Dio(
          BaseOptions(
            baseUrl: 'https://nominatim.openstreetmap.org',
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 10),
            headers: {'User-Agent': 'gildle-app (https://suvisdev.cloud/gildle)'},
          ),
        );

  final Dio _dio;

  Future<List<PlaceResult>> search(String query) async {
    final base = {'format': 'json', 'q': query, 'limit': 5, 'accept-language': 'ko'};
    var rows = await _get({...base, 'viewbox': '126.76,37.70,127.18,37.43', 'bounded': 1});
    if (rows.isEmpty) rows = await _get({...base, 'countrycodes': 'kr'});
    return rows;
  }

  Future<List<PlaceResult>> _get(Map<String, dynamic> params) async {
    final resp = await _dio.get<List<dynamic>>('/search', queryParameters: params);
    return (resp.data ?? const [])
        .cast<Map<String, dynamic>>()
        .map((r) => PlaceResult(
              name: r['display_name'] as String,
              point: GeoPoint(double.parse(r['lat'] as String), double.parse(r['lon'] as String)),
            ))
        .toList();
  }
}
