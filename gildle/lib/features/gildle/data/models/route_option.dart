import '../../domain/geo_point.dart';

/// 경로 곁 반려동물 장소(동물병원·펫샵·용품점·애견카페).
class PetPlace {
  const PetPlace({
    required this.id,
    required this.name,
    required this.category,
    required this.point,
    required this.address,
  });

  final String id;
  final String name;
  final String category;
  final GeoPoint point;
  final String address;

  factory PetPlace.fromJson(Map<String, dynamic> json) => PetPlace(
        id: json['id'] as String,
        name: json['name'] as String,
        category: json['category'] as String,
        point: GeoPoint((json['lat'] as num).toDouble(), (json['lng'] as num).toDouble()),
        address: json['address'] as String? ?? '',
      );
}

/// `POST /api/gildle/routes/options`·`/routes/via`·`/walk/plan`의 후보 하나 —
/// 빠른·그늘·푸른·편한·언덕길과 고를 이유. 웹(`suvis/lib/gildle-api.ts` RouteOption)과 같은 계약.
class RouteOption {
  const RouteOption({
    required this.kind,
    required this.label,
    required this.reason,
    required this.highlights,
    required this.recommended,
    required this.coordinates,
    required this.lengthM,
    this.shadeRatio,
    this.places = const [],
  });

  /// fast | shade | green | flat | hilly | via
  final String kind;
  final String label;
  final String reason;
  final List<String> highlights;
  final bool recommended;
  final List<GeoPoint> coordinates;
  final double lengthM;
  final double? shadeRatio;
  final List<PetPlace> places;

  factory RouteOption.fromJson(Map<String, dynamic> json) => RouteOption(
        kind: json['kind'] as String,
        label: json['label'] as String,
        reason: json['reason'] as String? ?? '',
        highlights: (json['highlights'] as List<dynamic>? ?? const []).cast<String>(),
        recommended: json['recommended'] as bool? ?? false,
        coordinates: (json['coordinates'] as List<dynamic>? ?? const [])
            .map((c) => GeoPoint.fromList(c as List<dynamic>))
            .toList(),
        lengthM: (json['length_m'] as num).toDouble(),
        shadeRatio: (json['shade_ratio'] as num?)?.toDouble(),
        places: (json['places'] as List<dynamic>? ?? const [])
            .map((p) => PetPlace.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}

class RouteOptionsResult {
  const RouteOptionsResult({required this.options, required this.night});

  final List<RouteOption> options;
  final bool night;

  factory RouteOptionsResult.fromJson(Map<String, dynamic> json) => RouteOptionsResult(
        options: _options(json['options']),
        night: json['night'] as bool? ?? false,
      );
}

/// `POST /api/gildle/walk/plan` — 문장·시간·거리·선호로 받은 산책 추천.
/// `kind`가 loop면 출발지로 돌아오고, route면 `destination`(가장 가까운 실제 장소)까지 간다.
class WalkPlan {
  const WalkPlan({
    required this.kind,
    required this.preferences,
    required this.stops,
    required this.source,
    required this.targetM,
    required this.options,
    required this.night,
    this.minutes,
    this.distanceKm,
    this.destinationCategory,
    this.destinationName,
    this.destination,
    this.viaName,
  });

  final String kind;
  final int? minutes;
  final double? distanceKm;
  /// 함께 적용된 선호 전부(첫 값이 대표).
  final List<String> preferences;
  final List<String> stops;
  final String? destinationCategory;

  /// llm | rules | form
  final String source;
  final String? destinationName;
  final GeoPoint? destination;
  final String? viaName;
  final double targetM;
  final List<RouteOption> options;
  final bool night;

  bool get returnsToStart => kind == 'loop';

  factory WalkPlan.fromJson(Map<String, dynamic> json) {
    final u = json['understood'] as Map<String, dynamic>;
    final dest = json['destination_place'] as Map<String, dynamic>?;
    final via = json['via_place'] as Map<String, dynamic>?;
    return WalkPlan(
      kind: u['kind'] as String,
      minutes: (u['minutes'] as num?)?.toInt(),
      distanceKm: (u['distance_km'] as num?)?.toDouble(),
      preferences: (u['preferences'] as List<dynamic>?)?.cast<String>() ?? [u['preference'] as String],
      stops: (u['stops'] as List<dynamic>? ?? const []).cast<String>(),
      destinationCategory: u['destination'] as String?,
      source: u['source'] as String,
      destinationName: dest?['name'] as String?,
      destination: dest == null
          ? null
          : GeoPoint((dest['lat'] as num).toDouble(), (dest['lng'] as num).toDouble()),
      viaName: via?['name'] as String?,
      targetM: (json['target_m'] as num).toDouble(),
      options: _options(json['options']),
      night: json['night'] as bool? ?? false,
    );
  }
}

List<RouteOption> _options(Object? raw) => (raw as List<dynamic>? ?? const [])
    .map((o) => RouteOption.fromJson(o as Map<String, dynamic>))
    .toList();
