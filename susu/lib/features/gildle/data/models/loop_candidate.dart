import '../../domain/geo_point.dart';

/// `POST /api/gildle/loops` 후보 하나 — 출발점으로 돌아오는 산책 루프.
class LoopCandidate {
  const LoopCandidate({
    required this.path,
    required this.coordinates,
    required this.lengthM,
    required this.overlapRatio,
    required this.bearingDeg,
    this.shadeRatio,
  });

  final List<String> path;
  final List<GeoPoint> coordinates;
  final double lengthM;
  final double overlapRatio;
  final double bearingDeg;
  final double? shadeRatio;

  factory LoopCandidate.fromJson(Map<String, dynamic> json) => LoopCandidate(
        path: (json['path'] as List<dynamic>).cast<String>(),
        coordinates: (json['coordinates'] as List<dynamic>)
            .map((c) => GeoPoint.fromList(c as List<dynamic>))
            .toList(),
        lengthM: (json['length_m'] as num).toDouble(),
        overlapRatio: (json['overlap_ratio'] as num).toDouble(),
        bearingDeg: (json['bearing_deg'] as num).toDouble(),
        shadeRatio: (json['shade_ratio'] as num?)?.toDouble(),
      );
}

class LoopResult {
  const LoopResult({required this.candidates, required this.night});

  final List<LoopCandidate> candidates;
  final bool night;

  factory LoopResult.fromJson(Map<String, dynamic> json) => LoopResult(
        candidates: (json['candidates'] as List<dynamic>)
            .map((c) => LoopCandidate.fromJson(c as Map<String, dynamic>))
            .toList(),
        night: json['night'] as bool? ?? false,
      );
}
