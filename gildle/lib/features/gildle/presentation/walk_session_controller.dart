import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../../core/network/dio_client.dart';
import '../data/gildle_route_api.dart';
import '../data/models/walk.dart';
import '../data/walks_api.dart';
import '../domain/geo_point.dart';
import '../domain/route_guidance.dart';
import '../domain/season_mode.dart';
import 'map_controller.dart';
import 'walk_alerts.dart';

final walksApiProvider = Provider<WalksApi>((ref) => WalksApi(ref.watch(dioProvider)));

enum WalkStatus { idle, tracking, stopped, saving, saved }

/// 지도 화면에서 넘겨받는 계획 경로(없어도 산책은 된다).
class PlannedRoute {
  const PlannedRoute({required this.coordinates, required this.mode, this.shadeRatio, this.kind});

  final List<GeoPoint> coordinates;

  /// 고른 후보의 성격(fast·shade…) — 이탈 후 새 길도 같은 성격으로 고른다.
  final String? kind;
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
    this.guidance,
    this.offRoute = false,
    this.rerouting = false,
    this.error,
    this.saved,
  });

  final WalkStatus status;
  final DateTime? startedAt;
  final List<GeoPoint> points;
  final double distanceM;
  final Duration elapsed;
  final PlannedRoute? planned;

  /// 계획 경로 기준 길 안내(경로 없이 걷거나 위치가 아직 없으면 null).
  final Guidance? guidance;
  final bool offRoute;

  /// 이탈 후 새 길을 받아 오는 중
  final bool rerouting;
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
    Guidance? guidance,
    bool? offRoute,
    bool? rerouting,
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
        guidance: guidance ?? this.guidance,
        offRoute: offRoute ?? this.offRoute,
        rerouting: rerouting ?? this.rerouting,
        error: clearError ? error : (error ?? this.error),
        saved: saved ?? this.saved,
      );
}

// 위치 잡음 필터 — 정확도가 나쁜 점은 버리고, 제자리 흔들림(2m 미만)은 거리에 안 더한다.
const _maxAccuracyM = 30.0;
const _minStepM = 2.0;
const _distanceFilterM = 5;

class WalkSessionController extends StateNotifier<WalkSessionState> {
  WalkSessionController(this._api, this._routes, this._alerts) : super(const WalkSessionState());

  final WalksApi _api;
  final GildleRouteApi _routes;
  final WalkAlerts _alerts;
  StreamSubscription<Position>? _positions;
  Timer? _ticker;
  RouteGuide? _guide;

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
    _guide = planned == null ? null : RouteGuide.build(planned.coordinates);
    if (_guide != null) unawaited(_alerts.init());
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
    final step = last?.distanceTo(p) ?? 0;
    if (last != null && step < _minStepM) return;
    final guidance = _guide?.locate(p, state.guidance?.progressM ?? 0);
    final wasOff = state.offRoute;
    final off = guidance == null ? false : isOffRoute(guidance.offM, wasOff: wasOff);
    state = state.copyWith(
      points: [...state.points, p],
      distanceM: state.distanceM + step,
      guidance: guidance,
      offRoute: off,
    );
    if (off && !wasOff) unawaited(_alerts.offRoute(guidance.offM));
    if (!off && wasOff) unawaited(_alerts.clear());
  }

  /// 이탈한 자리에서 새 길을 받는다. 목적지가 있는 길은 목적지까지, 돌아오는 코스는 원래 코스의
  /// 앞쪽 지점으로 합류하는 길을 받아 나머지 코스를 이어 붙인다.
  Future<void> reroute() async {
    final guide = _guide;
    final planned = state.planned;
    final here = state.current;
    if (guide == null || planned == null || here == null || state.rerouting) return;
    state = state.copyWith(rerouting: true);
    try {
      final target = guide.rejoinTarget(here, state.guidance?.progressM ?? 0);
      final found = (await _routes.options(start: here, end: target.point, mode: planned.mode)).options;
      if (found.isEmpty) throw StateError('no route');
      final picked = found.firstWhere(
        (o) => o.kind == planned.kind,
        orElse: () => found.firstWhere((o) => o.recommended, orElse: () => found.first),
      );
      final coords = [here, ...picked.coordinates, ...guide.remainderFrom(target.alongM)];
      _guide = RouteGuide.build(coords);
      state = WalkSessionState(
        status: state.status,
        startedAt: state.startedAt,
        points: state.points,
        distanceM: state.distanceM,
        elapsed: state.elapsed,
        planned: PlannedRoute(
          coordinates: coords,
          mode: planned.mode,
          shadeRatio: planned.shadeRatio,
          kind: planned.kind,
        ),
        guidance: _guide?.locate(here, 0),
      );
      unawaited(_alerts.clear());
    } catch (e) {
      state = state.copyWith(rerouting: false, error: '새 길을 찾지 못했어요. 점선 쪽으로 돌아가 주세요.');
    }
  }

  Future<void> stop() async {
    unawaited(_alerts.clear());
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
    unawaited(_alerts.clear());
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
  (ref) => WalkSessionController(
    ref.watch(walksApiProvider),
    ref.watch(gildleRouteApiProvider),
    ref.watch(walkAlertsProvider),
  ),
);
