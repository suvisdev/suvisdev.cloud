import 'package:flutter/material.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../../auth.dart';
import '../../../core/theme/gildle_theme.dart';
import '../data/models/route_option.dart';
import '../data/place_search_api.dart';
import '../domain/geo_point.dart';
import '../domain/season_mode.dart';
import 'format.dart';
import 'map_controller.dart';
import 'walk_screen.dart';
import 'walk_session_controller.dart';

const _seoulCenter = NLatLng(37.5665, 126.9780);
const _walkSpeedMps = 1.2; // 백엔드 `_WALK_SPEED_M_PER_S`와 같은 값

// 경로 후보 색 — 웹 지도 `KIND_COLOR`와 같은 값.
const _kindColors = <String, Color>{
  'fast': Color(0xFF60A5FA),
  'shade': Color(0xFF34D399),
  'green': Color(0xFFA3E635),
  'flat': Color(0xFF67E8F9),
  'hilly': Color(0xFFFB923C),
  'via': Color(0xFFF472B6),
};
const _prefLabels = <String, String>{
  'flat': '편한 길',
  'hilly': '언덕길',
  'shade': '그늘 많은 길',
  'green': '푸른 길',
  'fast': '빠른 길',
};
const _stopCategories = ['동물병원', '펫샵', '용품점', '애견카페'];
const _sourceLabels = {'llm': 'AI가 이해', 'rules': '문장에서 읽음', 'form': '직접 선택'};
const _routeNotice = '업데이트가 안된 경우에는 길이 조금 다를 수 있는 점 양해 부탁드리겠습니다.';
const _locationError = '현재 위치를 가져오지 못했어요. 위치 권한을 확인해 주세요.';

// 같은 성격의 후보가 여러 개일 때 서로 구분하는 색 — 웹 `INDEX_COLOR`와 같은 값.
const _indexColors = [
  Color(0xFF34D399),
  Color(0xFF60A5FA),
  Color(0xFFF472B6),
  Color(0xFFFB923C),
  Color(0xFFA3E635),
];

Color _kindColor(String kind) => _kindColors[kind] ?? _kindColors['shade']!;

/// 후보 i의 색 — 성격이 겹치면 순서별, 아니면 성격별.
Color _optionColor(MapState state, int i) =>
    state.sameKind ? _indexColors[i % _indexColors.length] : _kindColor(state.options[i].kind);

/// 후보 i의 이름 — 성격이 겹치면 "코스 N · 이름".
String _optionTitle(MapState state, int i) =>
    state.sameKind ? '코스 ${i + 1} · ${state.options[i].label}' : state.options[i].label;

/// 지도 — 출발·도착을 찍으면 경로 후보들을, 추천 버튼은 시간·거리에 맞춘 산책 코스를 그린다.
/// 웹 지도(`suvis/app/gildle/map`)와 같은 구성이다(2026-09-30 웹·앱 통일).
class GildleMapScreen extends ConsumerStatefulWidget {
  const GildleMapScreen({super.key});

  @override
  ConsumerState<GildleMapScreen> createState() => _GildleMapScreenState();
}

class _GildleMapScreenState extends ConsumerState<GildleMapScreen> {
  NaverMapController? _map;
  bool _locating = false;

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(mapControllerProvider);
    ref.listen<MapState>(mapControllerProvider, (prev, next) {
      final routeChanged = prev?.options != next.options || prev?.selected != next.selected;
      _syncOverlays(next, fit: routeChanged && next.displayedCoordinates.length >= 2);
    });

    return Scaffold(
      appBar: AppBar(title: const Text('길들')),
      body: Stack(
        children: [
          NaverMap(
            options: const NaverMapViewOptions(
              initialCameraPosition: NCameraPosition(target: _seoulCenter, zoom: 13),
              minZoom: 10,
              logoAlign: NLogoAlign.rightTop,
            ),
            onMapReady: (controller) {
              _map = controller;
              _syncOverlays(ref.read(mapControllerProvider), fit: false);
            },
            onMapTapped: (_, latLng) => ref
                .read(mapControllerProvider.notifier)
                .addPoint(GeoPoint(latLng.latitude, latLng.longitude)),
          ),
          if (state.loading) const Center(child: CircularProgressIndicator()),
          Positioned(left: 12, right: 12, bottom: 12, child: _BottomPanel(state: state)),
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _PlaceSearch(onSelect: _goToPlace),
                const SizedBox(height: 8),
                _ModeSelector(
                  mode: state.mode,
                  onChanged: (m) => ref.read(mapControllerProvider.notifier).setMode(m),
                ),
              ],
            ),
          ),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.endTop,
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(top: 124),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            FloatingActionButton.small(
              heroTag: 'me',
              tooltip: '내 위치로',
              onPressed: _locating ? null : _goToMe,
              child: const Icon(Icons.near_me),
            ),
            const SizedBox(height: 8),
            FloatingActionButton.small(
              heroTag: 'locate',
              tooltip: '현재 위치를 출발지로',
              onPressed: _locating ? null : _useCurrentLocation,
              child: _locating
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.my_location),
            ),
            const SizedBox(height: 8),
            FloatingActionButton.small(
              heroTag: 'loop',
              tooltip: '시간·거리로 돌아오는 산책 추천',
              onPressed: state.loading ? null : () => _showPlanSheet(context),
              child: const Icon(Icons.loop),
            ),
            const SizedBox(height: 8),
            FloatingActionButton.small(
              heroTag: 'clear',
              tooltip: '지우기',
              onPressed: () => ref.read(mapControllerProvider.notifier).clear(),
              child: const Icon(Icons.clear),
            ),
          ],
        ),
      ),
    );
  }

  /// 권한을 확인하고 현재 위치를 받는다. 못 받으면 안내를 띄우고 null.
  Future<GeoPoint?> _currentPosition() async {
    setState(() => _locating = true);
    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        _snack(_locationError);
        return null;
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      return GeoPoint(pos.latitude, pos.longitude);
    } catch (_) {
      _snack(_locationError);
      return null;
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _moveCamera(GeoPoint p, double zoom) async {
    await _map?.updateCamera(
      NCameraUpdate.scrollAndZoomTo(target: NLatLng(p.lat, p.lng), zoom: zoom),
    );
  }

  /// 내 위치로 화면만 옮긴다(출발지·경로는 그대로).
  Future<void> _goToMe() async {
    final here = await _currentPosition();
    if (here != null) await _moveCamera(here, 16);
  }

  Future<void> _useCurrentLocation() async {
    final here = await _currentPosition();
    if (here == null) return;
    await _moveCamera(here, 16);
    await ref.read(mapControllerProvider.notifier).setStart(here);
  }

  /// 검색에서 고른 장소 — 지도를 옮기고 탭과 같은 순서(출발→도착)로 찍는다.
  Future<void> _goToPlace(GeoPoint p) async {
    await _moveCamera(p, 15);
    await ref.read(mapControllerProvider.notifier).addPoint(p);
  }

  void _snack(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _showPlanSheet(BuildContext context) async {
    final request = await showModalBottomSheet<_PlanRequest>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => const _PlanSheet(),
    );
    if (request == null || !mounted) return;
    await ref.read(mapControllerProvider.notifier).planWalk(
          text: request.text,
          minutes: request.minutes,
          distanceKm: request.distanceKm,
          preferences: request.preferences,
          stops: request.stops,
        );
  }

  /// 상태 → 지도 오버레이. 매번 전부 지우고 다시 올린다(오버레이 수십 개 수준이라 충분).
  /// 후보를 모두 그린다 — 고른 것은 굵게·흰 외곽선, 나머지는 옅게(누르면 선택).
  Future<void> _syncOverlays(MapState state, {required bool fit}) async {
    final map = _map;
    if (map == null) return;
    final extras = Theme.of(context).extension<GildleExtras>()!;
    final accent = Theme.of(context).colorScheme.primary;
    final notifier = ref.read(mapControllerProvider.notifier);

    await map.clearOverlays();
    final overlays = <NAddableOverlay>{};
    final start = state.start;
    final end = state.end;
    if (start != null) {
      overlays.add(NMarker(
        id: 'start',
        position: NLatLng(start.lat, start.lng),
        caption: const NOverlayCaption(text: '출발'),
        iconTintColor: accent,
      ));
    }
    if (end != null) {
      overlays.add(NMarker(
        id: 'end',
        position: NLatLng(end.lat, end.lng),
        caption: const NOverlayCaption(text: '도착'),
        iconTintColor: extras.warm,
      ));
    }

    final all = <GeoPoint>[];
    final selected = state.option;
    for (var i = 0; i < state.options.length; i++) {
      final o = state.options[i];
      final coords = state.coordinatesOf(o);
      if (coords.length < 2) continue;
      all.addAll(coords);
      final line = coords.map((c) => NLatLng(c.lat, c.lng)).toList();
      if (i == state.selected) {
        overlays.add(NMultipartPathOverlay(
          id: 'route',
          width: 8,
          outlineWidth: 2,
          paths: [
            NMultipartPath(
              coords: line,
              color: _optionColor(state, i),
              outlineColor: Colors.white.withValues(alpha: 0.85),
            ),
          ],
        ));
        // 진행 방향 화살표 — 고른 경로 위에 일정 간격으로
        final arrows = directionArrows(coords);
        for (var k = 0; k < arrows.length; k++) {
          overlays.add(NArrowheadPathOverlay(
            id: 'arrow-$k',
            coords: [
              NLatLng(arrows[k].from.lat, arrows[k].from.lng),
              NLatLng(arrows[k].to.lat, arrows[k].to.lng),
            ],
            width: 3,
            color: Colors.white,
            outlineWidth: 1,
            outlineColor: const Color(0xFF0A0D0A),
            headSizeRatio: 3.2,
          ));
        }
        continue;
      }
      final other = NPolylineOverlay(
        id: 'option-$i',
        coords: line,
        color: _optionColor(state, i).withValues(alpha: 0.45),
        width: 6,
      )..setOnTapListener((_) => notifier.selectOption(i));
      overlays.add(other);
    }
    if (selected != null) {
      for (final place in selected.places) {
        overlays.add(NMarker(
          id: 'place-${place.id}',
          position: NLatLng(place.point.lat, place.point.lng),
          size: const Size(20, 26),
          iconTintColor: extras.warm,
          caption: NOverlayCaption(text: place.name, textSize: 11),
        ));
      }
    }
    await map.addOverlayAll(overlays);

    if (fit && all.length >= 2) {
      final bounds = NLatLngBounds.from(all.map((c) => NLatLng(c.lat, c.lng)));
      await map.updateCamera(
        NCameraUpdate.fitBounds(bounds, padding: const EdgeInsets.fromLTRB(60, 140, 60, 260)),
      );
    }
  }
}

/// 장소·주소 검색 — 웹 지도 검색창과 같은 역할. 제출하면 찾고, 고르면 그 자리를 찍는다.
class _PlaceSearch extends StatefulWidget {
  const _PlaceSearch({required this.onSelect});

  final ValueChanged<GeoPoint> onSelect;

  @override
  State<_PlaceSearch> createState() => _PlaceSearchState();
}

class _PlaceSearchState extends State<_PlaceSearch> {
  final _api = PlaceSearchApi();
  final _controller = TextEditingController();
  List<PlaceResult> _results = const [];
  bool _searching = false;
  String? _message;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search(String query) async {
    final q = query.trim();
    if (q.length < 2) return;
    setState(() {
      _searching = true;
      _message = null;
    });
    try {
      final results = await _api.search(q);
      if (!mounted) return;
      setState(() {
        _results = results;
        _message = results.isEmpty ? '검색 결과가 없어요.' : null;
      });
    } catch (_) {
      if (mounted) setState(() => _message = '장소를 검색하지 못했어요.');
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  void _pick(PlaceResult place) {
    _controller.text = place.shortName;
    FocusScope.of(context).unfocus();
    setState(() => _results = const []);
    widget.onSelect(place.point);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.extension<GildleExtras>()!.muted;
    final message = _message;
    return Material(
      color: theme.colorScheme.surface,
      elevation: 2,
      borderRadius: BorderRadius.circular(12),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _controller,
            textInputAction: TextInputAction.search,
            onSubmitted: _search,
            style: theme.textTheme.bodyMedium,
            decoration: InputDecoration(
              hintText: '장소·주소 검색 (예: 여의도공원)',
              hintStyle: TextStyle(color: muted),
              isDense: true,
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 12),
              prefixIcon: const Icon(Icons.search, size: 20),
              suffixIcon: _searching
                  ? const Padding(
                      padding: EdgeInsets.all(12),
                      child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                    )
                  : null,
            ),
          ),
          if (message != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: Text(message, style: theme.textTheme.bodySmall?.copyWith(color: muted)),
            ),
          for (final place in _results)
            ListTile(
              dense: true,
              title: Text(place.name, maxLines: 2, overflow: TextOverflow.ellipsis),
              onTap: () => _pick(place),
            ),
        ],
      ),
    );
  }
}

class _ModeSelector extends StatelessWidget {
  const _ModeSelector({required this.mode, required this.onChanged});

  final SeasonMode mode;
  final ValueChanged<SeasonMode> onChanged;

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<SeasonMode>(
      showSelectedIcon: false,
      style: SegmentedButton.styleFrom(
        backgroundColor: Theme.of(context).colorScheme.surface,
        visualDensity: VisualDensity.compact,
      ),
      segments: [
        for (final m in SeasonMode.values) ButtonSegment(value: m, label: Text(m.label)),
      ],
      selected: {mode},
      onSelectionChanged: (s) => onChanged(s.first),
    );
  }
}

class _BottomPanel extends ConsumerWidget {
  const _BottomPanel({required this.state});

  final MapState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final muted = theme.extension<GildleExtras>()!.muted;
    final option = state.option;
    final error = state.error;

    final String hint;
    if (state.start == null) {
      hint = '지도를 눌러 출발지를 정하세요';
    } else if (state.end == null && state.plan == null) {
      hint = '도착지를 누르거나 루프 버튼으로 시간·거리에 맞춰 돌아오는 길을 추천받으세요';
    } else {
      hint = '';
    }

    final String startLabel;
    if (option == null) {
      startLabel = '산책 시작';
    } else if (state.plan == null && option.kind != 'via') {
      startLabel = '${option.label}로 산책 시작';
    } else {
      startLabel = '이 길로 산책 시작';
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(error, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.error)),
              ),
            if (hint.isNotEmpty)
              Text(hint, style: theme.textTheme.bodyMedium?.copyWith(color: muted)),
            if (state.options.isNotEmpty)
              ConstrainedBox(
                constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.34),
                child: SingleChildScrollView(child: _OptionList(state: state)),
              ),
            if (option != null) ...[
              const SizedBox(height: 8),
              _Summary(option: option),
            ],
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => _startWalk(context, ref),
                icon: const Icon(Icons.directions_walk),
                label: Text(startLabel),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '© OpenStreetMap contributors · 보행 그래프 · 네이버 지도',
              style: theme.textTheme.labelSmall?.copyWith(color: muted),
            ),
          ],
        ),
      ),
    );
  }

  /// 경로가 있으면 계획 경로로 넘긴다 — 산책 중 화면이 회색 점선으로 깔고, 그늘 비율은 기록에 저장된다.
  /// 산책 기록은 로그인한 사용자만 저장한다 — 게스트면 먼저 로그인·가입 화면(돌아오면 이어서 시작).
  Future<void> _startWalk(BuildContext context, WidgetRef ref) async {
    if (!await ensureLoggedIn(context, ref) || !context.mounted) return;
    final planned = PlannedRoute(
      coordinates: state.displayedCoordinates,
      mode: state.mode,
      shadeRatio: state.option?.shadeRatio,
    );
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => WalkScreen(planned: planned)));
  }
}

/// 후보 카드 목록 — 추천 요약, 밤 안내, 후보(이유·요점), 곁의 반려동물 장소, 안내 문구.
class _OptionList extends ConsumerWidget {
  const _OptionList({required this.state});

  final MapState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final muted = theme.extension<GildleExtras>()!.muted;
    final small = theme.textTheme.labelSmall?.copyWith(color: muted);
    final notifier = ref.read(mapControllerProvider.notifier);
    final plan = state.plan;
    final places = state.option?.places ?? const <PetPlace>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (plan != null) Text(_planSummary(plan), style: small),
        if (state.night) Text('밤이라 그늘 길은 빼고 보여드려요.', style: small),
        for (var i = 0; i < state.options.length; i++)
          _OptionTile(
            option: state.options[i],
            title: _optionTitle(state, i),
            color: _optionColor(state, i),
            selected: i == state.selected,
            onTap: () => notifier.selectOption(i),
          ),
        if (places.isNotEmpty && plan != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              '🐾 이 코스 곁: ${places.map((p) => '${p.category} ${p.name}').join(' · ')}',
              style: small,
            ),
          ),
        if (places.isNotEmpty && plan == null) ...[
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 4),
            child: Text('🐾 이 길 곁 반려동물 장소 — 누르면 들렀다 가는 길을 만들어요', style: small),
          ),
          Wrap(
            spacing: 6,
            children: [
              for (final place in places)
                ActionChip(
                  visualDensity: VisualDensity.compact,
                  label: Text(
                    state.viaLoadingId == place.id ? '계산 중…' : '${place.category} · ${place.name}',
                  ),
                  onPressed: state.viaLoadingId != null ? null : () => notifier.viaPlace(place),
                ),
            ],
          ),
        ],
        const SizedBox(height: 4),
        Text(_routeNotice, style: small),
      ],
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.option,
    required this.title,
    required this.color,
    required this.selected,
    required this.onTap,
  });

  final RouteOption option;
  final String title;
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final extras = theme.extension<GildleExtras>()!;
    final accent = theme.colorScheme.primary;

    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Material(
        color: selected ? extras.surfaceAlt : Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: selected ? accent : extras.surfaceAlt),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 8),
                    Text(title, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
                    if (option.recommended) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: accent.withValues(alpha: 0.16),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text('추천', style: theme.textTheme.labelSmall?.copyWith(color: accent)),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  option.highlights.join(' · '),
                  style: theme.textTheme.labelSmall?.copyWith(color: extras.muted),
                ),
                const SizedBox(height: 2),
                Text(
                  option.reason,
                  maxLines: selected ? null : 1,
                  overflow: selected ? null : TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall?.copyWith(color: extras.muted),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({required this.option});

  final RouteOption option;

  @override
  Widget build(BuildContext context) {
    final minutes = (option.lengthM / _walkSpeedMps / 60).round().clamp(1, 100000);
    final shade = option.shadeRatio;

    return Row(
      children: [
        StatTile(label: '거리', value: formatKmShort(option.lengthM)),
        const SizedBox(width: 20),
        StatTile(label: '예상', value: '약 $minutes분'),
        if (shade != null) ...[
          const SizedBox(width: 20),
          StatTile(label: '그늘', value: '${(shade * 100).round()}%'),
        ],
      ],
    );
  }
}

/// 추천 요약 한 줄 — 웹 `PlanSummary`와 같은 순서.
String _planSummary(WalkPlan plan) {
  final distanceKm = plan.distanceKm;
  final parts = [
    if (plan.destinationName != null) '가장 가까운 ${plan.destinationName}까지',
    if (plan.viaName != null) '${plan.viaName} 들러서',
    if (plan.minutes != null) '${plan.minutes}분 안에',
    if (distanceKm != null) '${_trimNumber(distanceKm)}km',
    '목표 ${formatKmShort(plan.targetM)}',
    plan.preferences.map((k) => _prefLabels[k] ?? k).join(' + '),
    if (plan.stops.isNotEmpty) '${plan.stops.join('·')} 들르기',
  ];
  return '${parts.join(' · ')} (${_sourceLabels[plan.source] ?? plan.source})';
}

String _trimNumber(double v) => v == v.roundToDouble() ? v.toInt().toString() : v.toString();

class _PlanRequest {
  const _PlanRequest({
    this.text,
    this.minutes,
    this.distanceKm,
    required this.preferences,
    required this.stops,
  });

  final String? text;
  final int? minutes;
  final double? distanceKm;
  final List<String> preferences;
  final List<String> stops;
}

/// 시간·거리로 돌아오는 산책 추천 — 말로 적거나 직접 고른다(웹 추천 시트와 같은 입력).
class _PlanSheet extends StatefulWidget {
  const _PlanSheet();

  @override
  State<_PlanSheet> createState() => _PlanSheetState();
}

class _PlanSheetState extends State<_PlanSheet> {
  final _text = TextEditingController();
  final _minutes = TextEditingController();
  final _km = TextEditingController();
  final _preferences = <String>[]; // 고른 순서 유지 — 첫 값이 대표 선호
  final _stops = <String>{};

  @override
  void dispose() {
    _text.dispose();
    _minutes.dispose();
    _km.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _text.text.trim();
    final minutes = double.tryParse(_minutes.text.trim());
    final km = double.tryParse(_km.text.trim());
    Navigator.of(context).pop(_PlanRequest(
      text: text.isEmpty ? null : text,
      minutes: minutes != null && minutes > 0 ? minutes.round() : null,
      distanceKm: km != null && km > 0 ? km : null,
      preferences: List.of(_preferences),
      stops: _stopCategories.where(_stops.contains).toList(),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.extension<GildleExtras>()!.muted;
    final caption = theme.textTheme.labelMedium?.copyWith(color: muted);

    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(24, 0, 24, 24 + MediaQuery.viewInsetsOf(context).bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('시간·거리로 돌아오는 산책 추천', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('출발지에서 시작해 다시 출발지로 돌아오는 코스를 찾아요. 말로 적거나 직접 골라 주세요.', style: caption),
            const SizedBox(height: 12),
            TextField(
              controller: _text,
              maxLength: 300,
              minLines: 2,
              maxLines: 3,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: '예: 오늘은 40분 동안 3키로 정도 편하게 걷고, 가는 길에 사료 사고 싶어 · 동물병원으로 가는 최단 경로',
                hintMaxLines: 3,
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _minutes,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: '시간(분)', hintText: '예: 30'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: _km,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: '거리(km)', hintText: '예: 2'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text('어떤 길로? 여러 개 고를 수 있어요 (안 고르면 말한 대로, 없으면 편한 길)', style: caption),
            Wrap(
              spacing: 6,
              children: [
                for (final entry in _prefLabels.entries)
                  FilterChip(
                    label: Text(entry.value),
                    selected: _preferences.contains(entry.key),
                    onSelected: (on) => setState(
                      () => on ? _preferences.add(entry.key) : _preferences.remove(entry.key),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Text('🐾 가는 길에 들를 곳', style: caption),
            Wrap(
              spacing: 6,
              children: [
                for (final category in _stopCategories)
                  FilterChip(
                    label: Text(category),
                    selected: _stops.contains(category),
                    onSelected: (on) => setState(() => on ? _stops.add(category) : _stops.remove(category)),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('취소')),
                const SizedBox(width: 8),
                FilledButton(onPressed: _submit, child: const Text('코스 추천받기')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
