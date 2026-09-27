import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../data/gildle_route_api.dart';
import '../data/models/loop_candidate.dart';
import '../data/models/route_result.dart';
import '../domain/geo_point.dart';
import '../domain/season_mode.dart';

final gildleRouteApiProvider = Provider<GildleRouteApi>(
  (ref) => GildleRouteApi(ref.watch(dioProvider)),
);

/// 지도 화면 상태. 출발·도착이 다 찍히면 경로를, 루프를 요청하면 후보를 든다.
/// 둘 중 하나만 표시한다 — 루프 후보를 고르면 경로는 비우고, 점을 새로 찍으면 루프를 비운다.
class MapState {
  const MapState({
    this.start,
    this.end,
    this.mode = SeasonMode.springAutumn,
    this.route,
    this.loops = const [],
    this.selectedLoop,
    this.loading = false,
    this.error,
  });

  final GeoPoint? start;
  final GeoPoint? end;
  final SeasonMode mode;
  final RouteResult? route;
  final List<LoopCandidate> loops;
  final int? selectedLoop;
  final bool loading;
  final String? error;

  LoopCandidate? get currentLoop =>
      selectedLoop != null && selectedLoop! < loops.length ? loops[selectedLoop!] : null;

  /// 지도에 그릴 좌표열. 경로면 탭한 출발·도착점을 양 끝에 붙여 최근접 노드까지 잇는다.
  List<GeoPoint> get displayedCoordinates {
    final loop = currentLoop;
    if (loop != null) return loop.coordinates;
    final r = route;
    if (r == null || r.isEmpty) return const [];
    return [?start, ...r.coordinates, ?end];
  }

  /// 표시 중인 경로의 길이(m). 서버가 주면 그 값, 아니면 폴리라인에서 계산.
  double? get lengthM {
    final loop = currentLoop;
    if (loop != null) return loop.lengthM;
    final r = route;
    if (r == null || r.isEmpty) return null;
    return r.lengthM ?? polylineLengthM(r.coordinates);
  }

  MapState copyWith({
    GeoPoint? start,
    GeoPoint? end,
    SeasonMode? mode,
    RouteResult? route,
    List<LoopCandidate>? loops,
    int? selectedLoop,
    bool? loading,
    String? error,
    bool clearStart = false,
    bool clearEnd = false,
    bool clearRoute = false,
    bool clearLoops = false,
    bool clearError = true,
  }) =>
      MapState(
        start: clearStart ? null : (start ?? this.start),
        end: clearEnd ? null : (end ?? this.end),
        mode: mode ?? this.mode,
        route: clearRoute ? null : (route ?? this.route),
        loops: clearLoops ? const [] : (loops ?? this.loops),
        selectedLoop: clearLoops ? null : (selectedLoop ?? this.selectedLoop),
        loading: loading ?? this.loading,
        error: clearError ? error : (error ?? this.error),
      );
}

class MapController extends StateNotifier<MapState> {
  MapController(this._api) : super(const MapState());

  final GildleRouteApi _api;

  /// 첫 탭은 출발, 둘째 탭은 도착, 셋째 탭은 출발부터 다시(웹 지도와 같은 순서).
  Future<void> addPoint(GeoPoint p) async {
    if (state.start == null || state.end != null) {
      state = state.copyWith(start: p, clearEnd: true, clearRoute: true, clearLoops: true);
      return;
    }
    state = state.copyWith(end: p, clearLoops: true);
    await _fetchRoute();
  }

  Future<void> setStart(GeoPoint p) async {
    state = state.copyWith(start: p, clearRoute: true, clearLoops: true);
    if (state.end != null) await _fetchRoute();
  }

  Future<void> setMode(SeasonMode mode) async {
    if (mode == state.mode) return;
    state = state.copyWith(mode: mode, clearLoops: true);
    if (state.start != null && state.end != null) await _fetchRoute();
  }

  void clear() => state = MapState(mode: state.mode);

  Future<void> _fetchRoute() async {
    final start = state.start;
    final end = state.end;
    if (start == null || end == null) return;
    state = state.copyWith(loading: true, clearRoute: true);
    try {
      final result = await _api.route(start: start, end: end, mode: state.mode);
      state = state.copyWith(
        loading: false,
        route: result,
        error: result.isEmpty ? '경로를 찾을 수 없습니다. 서울 안의 보행로를 골라 주세요.' : null,
      );
    } catch (e) {
      state = state.copyWith(loading: false, error: describeApiError(e, '경로를'));
    }
  }

  /// 출발점에서 목표 거리만큼 돌아오는 루프 후보를 받는다. 도착점은 무시한다.
  Future<void> planLoops(double targetM) async {
    final start = state.start;
    if (start == null) {
      state = state.copyWith(error: '출발지를 먼저 찍어 주세요.');
      return;
    }
    state = state.copyWith(loading: true, clearEnd: true, clearRoute: true, clearLoops: true);
    try {
      final result = await _api.loops(start: start, targetM: targetM, mode: state.mode);
      state = state.copyWith(
        loading: false,
        loops: result.candidates,
        selectedLoop: result.candidates.isEmpty ? null : 0,
        error: result.candidates.isEmpty ? '이 거리로는 루프를 만들지 못했습니다.' : null,
      );
    } catch (e) {
      state = state.copyWith(loading: false, error: describeApiError(e, '루프를'));
    }
  }

  void selectLoop(int index) => state = state.copyWith(selectedLoop: index);
}

/// 에러 응답을 UI에 그대로 노출하지 않는다(.claude/rules/security/auth.md §6).
String describeApiError(Object error, String what) {
  if (error is DioException) {
    final status = error.response?.statusCode;
    if (status == 429) return '요청이 너무 많습니다. 잠시 후 다시 시도하세요.';
    if (status != null) return '$what 가져오지 못했습니다 (오류 코드 $status).';
    return '서버에 연결할 수 없습니다. 네트워크 상태를 확인하세요.';
  }
  return '$what 가져오지 못했습니다.';
}

final mapControllerProvider = StateNotifierProvider<MapController, MapState>(
  (ref) => MapController(ref.watch(gildleRouteApiProvider)),
);
