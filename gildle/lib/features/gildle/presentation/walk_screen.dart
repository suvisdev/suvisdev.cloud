import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/gildle_theme.dart';
import '../domain/geo_point.dart';
import '../domain/route_guidance.dart';
import 'format.dart';
import 'walk_detail_screen.dart';
import 'walk_session_controller.dart';

/// 산책 중 — 현재 위치를 따라가며 걸은 길을 그리고, 종료하면 `POST /walks`에 저장한다.
class WalkScreen extends ConsumerStatefulWidget {
  const WalkScreen({super.key, this.planned});

  final PlannedRoute? planned;

  @override
  ConsumerState<WalkScreen> createState() => _WalkScreenState();
}

class _WalkScreenState extends ConsumerState<WalkScreen> {
  NaverMapController? _map;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(walkSessionProvider.notifier).start(planned: widget.planned));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(walkSessionProvider);
    ref.listen<WalkSessionState>(walkSessionProvider, (prev, next) {
      if (prev?.points.length != next.points.length) _drawWalked(next);
      if (next.offRoute && prev?.offRoute != true) HapticFeedback.vibrate(); // 이탈하는 순간 한 번
      if (!identical(prev?.planned, next.planned)) _drawPlanned(next.planned); // 새 길을 받았을 때
      if (next.arrived && prev?.arrived != true) _confirmStop(); // 도착하면 끝낼지 한 번 묻는다
      if (next.error != null && prev?.error != next.error) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(next.error!)));
      }
    });

    return PopScope(
      canPop: state.status != WalkStatus.tracking,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _confirmStop();
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('산책 중')),
        body: Stack(
          children: [
            NaverMap(
              options: const NaverMapViewOptions(
                initialCameraPosition: NCameraPosition(target: NLatLng(37.5665, 126.9780), zoom: 15),
                locationButtonEnable: true,
              ),
              onMapReady: (c) async {
                _map = c;
                // 내비처럼 걷는 방향이 위로 오게 지도를 돌린다(지도를 끌면 SDK가 추적을 풀고, 위치 버튼으로 다시 켠다)
                c.setLocationTrackingMode(NLocationTrackingMode.face);
                await _drawPlanned(ref.read(walkSessionProvider).planned ?? widget.planned);
                await _drawWalked(ref.read(walkSessionProvider));
              },
            ),
            if (state.status == WalkStatus.tracking && state.guidance != null)
              Positioned(
                left: 12,
                right: 12,
                top: 12,
                child: _GuidanceCard(
                  guidance: state.guidance!,
                  offRoute: state.offRoute,
                  rerouting: state.rerouting,
                  onReroute: ref.read(walkSessionProvider.notifier).reroute,
                  voiceOn: state.voiceOn,
                  onToggleVoice: ref.read(walkSessionProvider.notifier).toggleVoice,
                ),
              ),
            Positioned(left: 12, right: 12, bottom: 12, child: _StatsCard(state: state, onStop: _confirmStop)),
          ],
        ),
      ),
    );
  }

  Future<void> _drawPlanned(PlannedRoute? planned) async {
    final map = _map;
    if (planned == null || map == null || planned.coordinates.length < 2) return;
    final muted = Theme.of(context).extension<GildleExtras>()!.muted;
    await map.clearOverlays(type: NOverlayType.arrowheadPathOverlay); // 새 길이면 옛 화살표를 지운다
    await map.addOverlay(NPolylineOverlay(
      id: 'planned',
      coords: planned.coordinates.map((c) => NLatLng(c.lat, c.lng)).toList(),
      color: muted.withValues(alpha: 0.7),
      width: 5,
      pattern: const [12, 8],
    ));
    // 진행 방향 화살표 — 지도 화면과 같은 규칙
    final arrows = directionArrows(planned.coordinates);
    await map.addOverlayAll({
      for (var k = 0; k < arrows.length; k++)
        NArrowheadPathOverlay(
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
        ),
    });
  }

  Future<void> _drawWalked(WalkSessionState state) async {
    final map = _map;
    if (map == null || state.points.length < 2) return;
    final accent = Theme.of(context).colorScheme.primary;
    await map.addOverlay(NPolylineOverlay(
      id: 'walked',
      coords: state.points.map((c) => NLatLng(c.lat, c.lng)).toList(),
      color: accent,
      width: 7,
    ));
  }

  Future<void> _confirmStop() async {
    final notifier = ref.read(walkSessionProvider.notifier);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('산책을 끝낼까요?'),
        content: const Text('끝내면 지금까지 걸은 길이 기록에 저장됩니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('계속 걷기')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('끝내기')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    await notifier.stop();
    if (!mounted) return;
    final state = ref.read(walkSessionProvider);
    if (state.points.length < 2) {
      final keep = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('위치가 잡히지 않았습니다'),
          content: const Text('걸은 길이 없어 저장할 내용이 없습니다. 기록을 버릴까요?'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('그래도 저장')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('버리기')),
          ],
        ),
      );
      if (keep == true) {
        notifier.discard();
        if (mounted) Navigator.of(context).pop();
        return;
      }
    }
    final saved = await notifier.save();
    if (!mounted) return;
    if (saved) {
      final detail = ref.read(walkSessionProvider).saved!;
      notifier.discard();
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => WalkDetailScreen(id: detail.id, initial: detail)),
      );
    }
  }
}

/// 다음 방향 한 줄 + 남은 거리. 경로를 벗어나면 경고색으로 바뀐다.
class _GuidanceCard extends StatelessWidget {
  const _GuidanceCard({
    required this.guidance,
    required this.offRoute,
    required this.rerouting,
    required this.onReroute,
    required this.voiceOn,
    required this.onToggleVoice,
  });

  final Guidance guidance;
  final bool offRoute;
  final bool rerouting;
  final VoidCallback onReroute;
  final bool voiceOn;
  final VoidCallback onToggleVoice;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.extension<GildleExtras>()!.muted;
    final icon = offRoute
        ? Icons.warning_amber_rounded
        : switch (guidance.next?.side) {
            TurnSide.left => Icons.turn_left,
            TurnSide.right => Icons.turn_right,
            TurnSide.back => Icons.u_turn_left,
            null => Icons.straight,
          };
    return Card(
      color: offRoute ? theme.colorScheme.errorContainer : null,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            Icon(icon, size: 28, color: offRoute ? theme.colorScheme.onErrorContainer : theme.colorScheme.primary),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                guidanceText(guidance, offRoute: offRoute),
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: offRoute ? theme.colorScheme.onErrorContainer : null,
                ),
              ),
            ),
            if (offRoute)
              FilledButton.tonal(
                onPressed: rerouting ? null : onReroute,
                child: Text(rerouting ? '찾는 중…' : '새 길 찾기'),
              ),
            if (!offRoute)
              Text('남은 ${formatKmShort(guidance.remainingM)}', style: theme.textTheme.labelSmall?.copyWith(color: muted)),
            IconButton(
              tooltip: voiceOn ? '음성 안내 끄기' : '음성 안내 켜기',
              onPressed: onToggleVoice,
              icon: Icon(voiceOn ? Icons.volume_up : Icons.volume_off, size: 20),
              color: offRoute ? theme.colorScheme.onErrorContainer : muted,
              visualDensity: VisualDensity.compact,
            ),
          ],
        ),
      ),
    );
  }
}

class _StatsCard extends StatelessWidget {
  const _StatsCard({required this.state, required this.onStop});

  final WalkSessionState state;
  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    final pace = state.paceMinPerKm;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                StatTile(label: '거리', value: formatKm(state.distanceM)),
                StatTile(label: '시간', value: formatDuration(state.elapsed)),
                StatTile(label: '페이스', value: pace == null ? '—' : '${pace.toStringAsFixed(1)}분/km'),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: state.status == WalkStatus.tracking ? onStop : null,
                icon: state.status == WalkStatus.saving
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.stop),
                label: Text(state.status == WalkStatus.saving ? '저장 중…' : '산책 끝내기'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

