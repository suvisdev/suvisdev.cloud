import '../../domain/geo_point.dart';

/// `POST /api/gildle/routes` · `/navigate` 응답.
/// `shade_ratio`·`edge_shades`·`night`는 여름 모드에서만 채워진다.
class RouteResult {
  const RouteResult({
    required this.path,
    required this.coordinates,
    this.shadeRatio,
    this.edgeShades,
    this.night = false,
    this.lengthM,
  });

  final List<String> path;
  final List<GeoPoint> coordinates;
  final double? shadeRatio;
  final List<double>? edgeShades;
  final bool night;
  final double? lengthM;

  bool get isEmpty => path.isEmpty;

  factory RouteResult.fromJson(Map<String, dynamic> json) => RouteResult(
        path: (json['path'] as List<dynamic>? ?? const []).cast<String>(),
        coordinates: (json['coordinates'] as List<dynamic>? ?? const [])
            .map((c) => GeoPoint.fromList(c as List<dynamic>))
            .toList(),
        shadeRatio: (json['shade_ratio'] as num?)?.toDouble(),
        edgeShades: (json['edge_shades'] as List<dynamic>?)
            ?.map((v) => (v as num).toDouble())
            .toList(),
        night: json['night'] as bool? ?? false,
        lengthM: (json['length_m'] as num?)?.toDouble(),
      );
}
