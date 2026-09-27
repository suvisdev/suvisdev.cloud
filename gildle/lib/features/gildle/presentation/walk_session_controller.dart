import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../../core/network/dio_client.dart';
import '../data/models/walk.dart';
import '../data/walks_api.dart';
import '../domain/geo_point.dart';
import '../domain/season_mode.dart';
import 'map_controller.dart';

final walksApiProvider = Provider<WalksApi>((ref) => WalksApi(ref.watch(dioProvider)));

enum WalkStatus { idle, tracking, stopped, saving, saved }

/// 지도 화면에서 넘겨받는 계획 경로(없어도 산책은 된다).
class PlannedRoute {
  const PlannedRoute({required this.coordinates, required this.mode, this.shadeRatio});

  final List<GeoPoint> coordinates;
  final SeasonMode mode;
  final double? shadeRatio;
}

class WalkSessionState {
  const WalkSessionState({
    this.status = WalkStatus.idle,
    this.startedAt,
    this.points = const [],
    this.distanceM = 0,
    this.elapsed = Duration.zero,
    this.planned,
    this.error,
    this.saved,
  });

  final WalkStatus status;
  final DateTime? startedAt;
  final List<GeoPoint> points;
  final double distanceM;
  final Duration elapsed;
  final PlannedRoute? planned;
  final String? error;
  final WalkDetail? saved;

  GeoPoint? get current => points.isEmpty ? null : points.last;

  /// 분/km. 100m 미만이면 의미 없어 null.
  double? get paceMinPerKm =>
      distanceM < 100 ? null : (elapsed.inSeconds / 60) / (distanceM / 1000);

  WalkSessionState copyWith({
    WalkStatus? status,
    DateTime? startedAt,
    List<GeoPoint>? points,
    double? distanceM,
    Duration? elapsed,
    PlannedRoute? planned,
    String? error,
    WalkDetail? saved,
    bool clearError = true,
  }) =>
      WalkSessionState(
        status: status ?? this.status,
        startedAt: startedAt ?? this.startedAt,
        points: points ?? this.points,
        distanceM: distanceM ?? this.distanceM,
        elapsed: elapsed ?? this.elapsed,
        planned: planned ?? this.planned,
        error: clearError ? error : (error ?? this.error),
        saved: saved ?? this.saved,
      );
}

// 위치 잡음 필터 — 정확도가 나쁜 점은 버리고, 제자리 흔들림(2m 미만)은 거리에 안 더한다.
const _maxAccuracyM = 30.0;
const _minStepM = 2.0;
const _distanceFilterM = 5;

class WalkSessionController extends StateNotifier<WalkSessionState> {
  WalkSessionController(this._api) : super(const WalkSessionState());

  final WalksApi _api;
  StreamSubscription<Position>? _positions;
  Timer? _ticker;

  Future<void> start({PlannedRoute? planned}) async {
    if (state.status == WalkStatus.tracking) return;
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      state = state.copyWith(error: '위치 권한이 없어 산책을 기록할 수 없습니다.');
      return;
    }
    final startedAt = DateTime.now();
    state = WalkSessionState(status: WalkStatus.tracking, startedAt: startedAt, planned: planned);
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (state.status == WalkStatus.tracking) {
        state = state.copyWith(elapsed: DateTime.now().difference(startedAt));
      }
    });
    // 포그라운드 서비스 알림으로 화면이 꺼져도 추적이 이어진다(백그라운드 위치 권한은 불필요).
    _positions = Geolocator.getPositionStream(
      locationSettings: AndroidSettings(
        accuracy: LocationAccuracy.best,
        distanceFilter: _distanceFilterM,
        foregroundNotificationConfig: const ForegroundNotificationConfig(
          notificationTitle: '길들 산책 중',
          notificationText: '걷는 길을 기록하고 있습니다',
          notificationChannelName: '산책 기록',
          setOngoing: true,
        ),
      ),
    ).listen(_onPosition, onError: (Object e) {
      state = state.copyWith(error: '위치를 받지 못했습니다.', clearError: false);
    });
  }

  void _onPosition(Position pos) {
    if (state.status != WalkStatus.tracking) return;
    if (pos.accuracy > _maxAccuracyM) return;
    final p = GeoPoint(pos.latitude, pos.longitude);
    final last = state.current;
    if (last == null) {
      state = state.copyWith(points: [p]);
      return;
    }
    final step = last.distanceTo(p);
    if (step < _minStepM) return;
    state = state.copyWith(points: [...state.points, p], distanceM: state.distanceM + step);
  }

  Future<void> stop() async {
    await _positions?.cancel();
    _positions = null;
    _ticker?.cancel();
    _ticker = null;
    final startedAt = state.startedAt;
    state = state.copyWith(
      status: WalkStatus.stopped,
      elapsed: startedAt == null ? state.elapsed : DateTime.now().difference(startedAt),
    );
  }

  Future<bool> save() async {
    if (state.status != WalkStatus.stopped || state.startedAt == null) return false;
    state = state.copyWith(status: WalkStatus.saving);
    try {
      final saved = await _api.create(
        startedAt: state.startedAt!,
        endedAt: state.startedAt!.add(state.elapsed),
        distanceM: state.distanceM.round(),
        durationS: state.elapsed.inSeconds,
        path: state.points,
        seasonMode: (state.planned?.mode ?? SeasonMode.springAutumn).apiValue,
        avgShadeScore: state.planned?.shadeRatio,
      );
      state = state.copyWith(status: WalkStatus.saved, saved: saved);
      return true;
    } catch (e) {
      state = state.copyWith(status: WalkStatus.stopped, error: describeApiError(e, '기록을'));
      return false;
    }
  }

  void discard() {
    _positions?.cancel();
    _ticker?.cancel();
    state = const WalkSessionState();
  }

  @override
  void dispose() {
    _positions?.cancel();
    _ticker?.cancel();
    super.dispose();
  }
}

final walkSessionProvider = StateNotifierProvider<WalkSessionController, WalkSessionState>(
  (ref) => WalkSessionController(ref.watch(walksApiProvider)),
);
