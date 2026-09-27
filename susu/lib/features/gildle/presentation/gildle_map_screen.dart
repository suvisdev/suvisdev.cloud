import 'package:flutter/material.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../../core/theme/gildle_theme.dart';
import '../domain/geo_point.dart';
import '../domain/season_mode.dart';
import 'format.dart';
import 'map_controller.dart';
import 'walk_screen.dart';
import 'walk_session_controller.dart';

const _seoulCenter = NLatLng(37.5665, 126.9780);
const _walkSpeedMps = 1.2; // 백엔드 `_WALK_SPEED_M_PER_S`와 같은 값

/// 지도 — 출발·도착을 찍으면 계절 모드 경로를, 루프 버튼은 출발점 기준 산책 루프를 그린다.
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
      final routeChanged = prev?.route != next.route || prev?.selectedLoop != next.selectedLoop;
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
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: _ModeSelector(
              mode: state.mode,
              onChanged: (m) => ref.read(mapControllerProvider.notifier).setMode(m),
            ),
          ),
          if (state.loading) const Center(child: CircularProgressIndicator()),
          Positioned(left: 12, right: 12, bottom: 12, child: _BottomPanel(state: state)),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.endTop,
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(top: 64),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
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
              tooltip: '돌아오는 산책 루프',
              onPressed: () => _showLoopSheet(context),
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

  Future<void> _useCurrentLocation() async {
    setState(() => _locating = true);
    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        _snack('위치 권한이 없어 현재 위치를 쓸 수 없습니다.');
        return;
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      final here = GeoPoint(pos.latitude, pos.longitude);
      await ref.read(mapControllerProvider.notifier).setStart(here);
      await _map?.updateCamera(
        NCameraUpdate.scrollAndZoomTo(target: NLatLng(here.lat, here.lng), zoom: 16),
      );
    } catch (_) {
      _snack('현재 위치를 가져오지 못했습니다.');
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  void _snack(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _showLoopSheet(BuildContext context) async {
    final targetM = await showModalBottomSheet<double>(
      context: context,
      showDragHandle: true,
      builder: (_) => const _LoopSheet(),
    );
    if (targetM == null || !mounted) return;
    await ref.read(mapControllerProvider.notifier).planLoops(targetM);
  }

  /// 상태 → 지도 오버레이. 매번 전부 지우고 다시 올린다(오버레이 수십 개 수준이라 충분).
  Future<void> _syncOverlays(MapState state, {required bool fit}) async {
    final map = _map;
    if (map == null) return;
    final extras = Theme.of(context).extension<GildleExtras>()!;
    final accent = Theme.of(context).colorScheme.primary;

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

    final coords = state.displayedCoordinates;
    if (coords.length >= 2) {
      overlays.add(_pathOverlay(state, coords, shade: accent, sun: extras.warm));
    }
    await map.addOverlayAll(overlays);

    if (fit) {
      final bounds = NLatLngBounds.from(coords.map((c) => NLatLng(c.lat, c.lng)));
      await map.updateCamera(
        NCameraUpdate.fitBounds(bounds, padding: const EdgeInsets.fromLTRB(60, 120, 60, 200)),
      );
    }
  }

  /// 여름 모드는 구간별 그늘 비율로 색을 섞고(햇빛=warm, 그늘=accent), 그 외는 단색.
  NMultipartPathOverlay _pathOverlay(
    MapState state,
    List<GeoPoint> coords, {
    required Color shade,
    required Color sun,
  }) {
    final shades = state.currentLoop == null ? state.route?.edgeShades : null;
    final outline = Colors.white.withValues(alpha: 0.8);
    if (state.mode != SeasonMode.summerShade || shades == null || shades.isEmpty) {
      return NMultipartPathOverlay(
        id: 'route',
        width: 8,
        outlineWidth: 2,
        paths: [
          NMultipartPath(
            coords: coords.map((c) => NLatLng(c.lat, c.lng)).toList(),
            color: shade,
            outlineColor: outline,
          ),
        ],
      );
    }
    // displayedCoordinates는 [탭한 출발, 노드들…, 탭한 도착]이라 구간 수가 간선 수 + 2다.
    // 앞뒤 연결 구간은 이웃 간선의 그늘을 쓴다.
    final paths = <NMultipartPath>[];
    for (var i = 0; i + 1 < coords.length; i++) {
      final edgeIdx = (i - 1).clamp(0, shades.length - 1);
      final color = Color.lerp(sun, shade, shades[edgeIdx].clamp(0.0, 1.0))!;
      paths.add(NMultipartPath(
        coords: [NLatLng(coords[i].lat, coords[i].lng), NLatLng(coords[i + 1].lat, coords[i + 1].lng)],
        color: color,
        outlineColor: outline,
      ));
    }
    return NMultipartPathOverlay(id: 'route', width: 8, outlineWidth: 2, paths: paths);
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
    final lengthM = state.lengthM;

    final String hint;
    if (state.error != null) {
      hint = state.error!;
    } else if (state.start == null) {
      hint = '지도를 눌러 출발지를 정하세요';
    } else if (state.end == null && state.loops.isEmpty) {
      hint = '도착지를 누르거나 루프 버튼으로 돌아오는 길을 만드세요';
    } else {
      hint = '';
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (hint.isNotEmpty)
              Text(hint, style: theme.textTheme.bodyMedium?.copyWith(color: muted)),
            if (lengthM != null) _Summary(state: state, lengthM: lengthM),
            if (state.loops.length > 1) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  for (var i = 0; i < state.loops.length; i++)
                    ChoiceChip(
                      label: Text('${_km(state.loops[i].lengthM)} · ${_bearing(state.loops[i].bearingDeg)}'),
                      selected: state.selectedLoop == i,
                      onSelected: (_) => ref.read(mapControllerProvider.notifier).selectLoop(i),
                    ),
                ],
              ),
            ],
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => _startWalk(context),
                icon: const Icon(Icons.directions_walk),
                label: Text(lengthM != null ? '이 길로 산책 시작' : '산책 시작'),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '경로 데이터 © OpenStreetMap contributors',
              style: theme.textTheme.labelSmall?.copyWith(color: muted),
            ),
          ],
        ),
      ),
    );
  }

  /// 경로가 있으면 계획 경로로 넘긴다 — 산책 중 화면이 회색 점선으로 깔고, 그늘 비율은 기록에 저장된다.
  void _startWalk(BuildContext context) {
    final coords = state.displayedCoordinates;
    final loop = state.currentLoop;
    final planned = coords.length >= 2
        ? PlannedRoute(
            coordinates: coords,
            mode: state.mode,
            shadeRatio: loop != null ? loop.shadeRatio : state.route?.shadeRatio,
          )
        : PlannedRoute(coordinates: const [], mode: state.mode);
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => WalkScreen(planned: planned)));
  }
}

class _Summary extends StatelessWidget {
  const _Summary({required this.state, required this.lengthM});

  final MapState state;
  final double lengthM;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final minutes = (lengthM / _walkSpeedMps / 60).round();
    final loop = state.currentLoop;
    final shade = loop != null ? loop.shadeRatio : state.route?.shadeRatio;
    final night = loop == null && (state.route?.night ?? false);

    return Row(
      children: [
        StatTile(label: '거리', value: _km(lengthM)),
        const SizedBox(width: 20),
        StatTile(label: '예상', value: '약 $minutes분'),
        if (state.mode == SeasonMode.summerShade) ...[
          const SizedBox(width: 20),
          if (night)
            Text('밤이라 그늘 계산 없이 최단 경로', style: theme.textTheme.bodySmall)
          else if (shade != null)
            StatTile(label: '그늘', value: '${(shade * 100).round()}%'),
        ],
      ],
    );
  }
}

class _LoopSheet extends StatefulWidget {
  const _LoopSheet();

  @override
  State<_LoopSheet> createState() => _LoopSheetState();
}

class _LoopSheetState extends State<_LoopSheet> {
  double _km = 2.0;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('출발지로 돌아오는 산책', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('목표 거리 ${_km.toStringAsFixed(1)} km'),
            Slider(
              value: _km,
              min: 0.5,
              max: 8,
              divisions: 15,
              label: '${_km.toStringAsFixed(1)} km',
              onChanged: (v) => setState(() => _km = v),
            ),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () => Navigator.of(context).pop(_km * 1000),
                child: const Text('루프 만들기'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _km(double m) => m >= 1000 ? '${(m / 1000).toStringAsFixed(1)} km' : '${m.round()} m';

String _bearing(double deg) {
  const names = ['북', '북동', '동', '남동', '남', '남서', '서', '북서'];
  return names[((deg % 360) / 45).round() % 8];
}
