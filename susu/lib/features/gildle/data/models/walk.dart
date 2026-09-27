import '../../domain/geo_point.dart';

/// `GET /api/gildle/walks` 목록 항목(경로 좌표 없음 — 응답 크기).
class WalkSummary {
  const WalkSummary({
    required this.id,
    required this.startedAt,
    required this.endedAt,
    required this.distanceM,
    required this.durationS,
    required this.seasonMode,
    this.avgShadeScore,
  });

  final int id;
  final DateTime startedAt;
  final DateTime endedAt;
  final int distanceM;
  final int durationS;
  final String seasonMode;
  final double? avgShadeScore;

  factory WalkSummary.fromJson(Map<String, dynamic> json) => WalkSummary(
        id: json['id'] as int,
        startedAt: DateTime.parse(json['started_at'] as String).toLocal(),
        endedAt: DateTime.parse(json['ended_at'] as String).toLocal(),
        distanceM: json['distance_m'] as int,
        durationS: json['duration_s'] as int,
        seasonMode: json['season_mode'] as String,
        avgShadeScore: (json['avg_shade_score'] as num?)?.toDouble(),
      );
}

/// `GET /api/gildle/walks/{id}` — 좌표열·메모 포함.
class WalkDetail extends WalkSummary {
  const WalkDetail({
    required super.id,
    required super.startedAt,
    required super.endedAt,
    required super.distanceM,
    required super.durationS,
    required super.seasonMode,
    super.avgShadeScore,
    required this.path,
    this.memo,
  });

  final List<GeoPoint> path;
  final String? memo;

  factory WalkDetail.fromJson(Map<String, dynamic> json) {
    final s = WalkSummary.fromJson(json);
    return WalkDetail(
      id: s.id,
      startedAt: s.startedAt,
      endedAt: s.endedAt,
      distanceM: s.distanceM,
      durationS: s.durationS,
      seasonMode: s.seasonMode,
      avgShadeScore: s.avgShadeScore,
      path: (json['path'] as List<dynamic>? ?? const [])
          .map((c) => GeoPoint.fromList(c as List<dynamic>))
          .toList(),
      memo: json['memo'] as String?,
    );
  }
}

class WalkStats {
  const WalkStats({
    required this.totalCount,
    required this.totalDistanceM,
    required this.totalDurationS,
  });

  final int totalCount;
  final int totalDistanceM;
  final int totalDurationS;

  factory WalkStats.fromJson(Map<String, dynamic> json) => WalkStats(
        totalCount: json['total_count'] as int,
        totalDistanceM: json['total_distance_m'] as int,
        totalDurationS: json['total_duration_s'] as int,
      );
}
