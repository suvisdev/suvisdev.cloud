import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../data/gildle_route_api.dart';
import '../data/models/route_option.dart';
import '../domain/geo_point.dart';
import '../domain/season_mode.dart';

final gildleRouteApiProvider = Provider<GildleRouteApi>(
  (ref) => GildleRouteApi(ref.watch(dioProvider)),
);

/// 지도 화면 상태 — 웹 지도(`gildle-map.tsx`)와 같은 모델(2026-09-30 웹·앱 통일).
/// 출발·도착이 다 찍히면 경로 후보들을, 추천을 요청하면 `plan`과 그 후보들을 든다.
class MapState {
  const MapState({
    this.start,
    this.end,
    this.mode = SeasonMode.springAutumn,
    this.options = const [],
    this.selected = 0,
    this.plan,
    this.night = false,
    this.loading = false,
    this.viaLoadingId,
    this.error,
  });

  final GeoPoint? start;
  final GeoPoint? end;
  final SeasonMode mode;
  final List<RouteOption> options;
  final int selected;

  /// 시간·거리로 추천받은 결과면 채워진다(이때 options는 그 추천의 후보들).
  final WalkPlan? plan;
  final bool night;
  final bool loading;

  /// 들렀다 가는 길을 계산 중인 장소 id.
  final String? viaLoadingId;
  final String? error;

  RouteOption? get option => selected < options.length ? options[selected] : null;

  /// 출발지로 돌아오는 코스인가(추천 중 loop).
  bool get returnsToStart => plan?.returnsToStart ?? false;

  /// 후보 좌표 앞뒤에 탭한 지점을 붙여 최근접 노드까지 잇는다(루프는 출발지로 돌아온다).
  List<GeoPoint> coordinatesOf(RouteOption o) {
    final s = start;
    final tail = returnsToStart ? start : end;
    if (s == null || tail == null || o.coordinates.isEmpty) return const [];
    return [s, ...o.coordinates, tail];
  }

  /// 지도에 굵게 그릴(고른) 후보의 좌표열.
  List<GeoPoint> get displayedCoordinates {
    final o = option;
    return o == null ? const [] : coordinatesOf(o);
  }

  double? get lengthM => option?.lengthM;
}

class MapController extends StateNotifier<MapState> {
  MapController(this._api) : super(const MapState());

  final GildleRouteApi _api;

  /// 첫 탭은 출발, 둘째 탭은 도착, 셋째 탭은 출발부터 다시(웹 지도와 같은 순서).
  Future<void> addPoint(GeoPoint p) async {
    final s = state.start;
    if (s == null || state.end != null) {
      state = MapState(start: p, mode: state.mode);
      return;
    }
    await _fetchOptions(s, p);
  }

  /// 현재 위치를 출발지로 — 도착지가 있으면 경로를 다시 구한다.
  Future<void> setStart(GeoPoint p) async {
    final e = state.plan == null ? state.end : null;
    if (e == null) {
      state = MapState(start: p, mode: state.mode);
      return;
    }
    await _fetchOptions(p, e);
  }

  Future<void> setMode(SeasonMode mode) async {
    if (mode == state.mode) return;
    final s = state.start;
    final e = state.end;
    state = _copy(mode: mode);
    // 추천받은 코스는 계절 모드와 무관하게 정해졌으니 다시 구하지 않는다.
    if (s != null && e != null && state.plan == null) await _fetchOptions(s, e);
  }

  void clear() => state = MapState(mode: state.mode);

  void selectOption(int index) => state = _copy(selected: index);

  Future<void> _fetchOptions(GeoPoint start, GeoPoint end) async {
    state = MapState(start: start, end: end, mode: state.mode, loading: true);
    try {
      final result = await _api.options(start: start, end: end, mode: state.mode);
      state = MapState(
        start: start,
        end: end,
        mode: state.mode,
        options: result.options,
        selected: _recommended(result.options),
        night: result.night,
        error: result.options.isEmpty ? '두 지점을 잇는 보행 경로를 찾지 못했어요.' : null,
      );
    } catch (e) {
      state = MapState(
        start: start,
        end: end,
        mode: state.mode,
        error: describeApiError(e, '경로를'),
      );
    }
  }

  /// 고른 장소에 들렀다 가는 경로 — 지금 고른 후보와 같은 성격으로 계산해 후보 목록 끝에 붙인다.
  Future<void> viaPlace(PetPlace place) async {
    final s = state.start;
    final e = state.end;
    final current = state.option;
    if (s == null || e == null || current == null || state.plan != null) return;
    state = _copy(viaLoadingId: place.id);
    try {
      final via = await _api.via(
        start: s,
        end: e,
        mode: state.mode,
        place: place,
        baseKind: current.kind == 'via' ? 'fast' : current.kind,
      );
      final rest = state.options.where((o) => o.kind != 'via').toList();
      state = _copy(options: [...rest, via], selected: rest.length);
    } catch (err) {
      state = _copy(error: describeApiError(err, '들렀다 가는 길을'));
    }
  }

  /// 문장·시간·거리·선호·들를 곳으로 산책을 추천받는다. 출발지가 기준이고 도착점은 서버가 정한다.
  Future<void> planWalk({
    String? text,
    int? minutes,
    double? distanceKm,
    String? preference,
    List<String> stops = const [],
  }) async {
    final s = state.start;
    if (s == null) {
      state = _copy(error: '먼저 출발지를 정해 주세요.');
      return;
    }
    state = MapState(start: s, mode: state.mode, loading: true);
    try {
      final plan = await _api.plan(
        start: s,
        text: text,
        minutes: minutes,
        distanceKm: distanceKm,
        preference: preference,
        stops: stops,
      );
      state = MapState(
        start: s,
        end: plan.destination,
        mode: state.mode,
        options: plan.options,
        selected: _recommended(plan.options),
        plan: plan,
        night: plan.night,
        error: plan.options.isEmpty ? _emptyPlanMessage(plan) : null,
      );
    } catch (e) {
      state = MapState(start: s, mode: state.mode, error: describeApiError(e, '코스를'));
    }
  }

  /// error·viaLoadingId는 넘기지 않으면 지운다(다음 동작에서 묵은 오류가 남지 않게).
  MapState _copy({
    SeasonMode? mode,
    List<RouteOption>? options,
    int? selected,
    String? viaLoadingId,
    String? error,
  }) =>
      MapState(
        start: state.start,
        end: state.end,
        mode: mode ?? state.mode,
        options: options ?? state.options,
        selected: selected ?? state.selected,
        plan: state.plan,
        night: state.night,
        viaLoadingId: viaLoadingId,
        error: error,
      );
}

int _recommended(List<RouteOption> options) {
  final i = options.indexWhere((o) => o.recommended);
  return i < 0 ? 0 : i;
}

String _emptyPlanMessage(WalkPlan plan) {
  final category = plan.destinationCategory;
  if (category == null) return '돌아오는 코스를 찾지 못했어요. 시간이나 거리를 바꿔 보세요.';
  final name = plan.destinationName;
  return name != null ? '$name까지 가는 길을 찾지 못했어요.' : '근처 3km 안에서 $category을(를) 찾지 못했어요.';
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
